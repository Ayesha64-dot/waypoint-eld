"""HOS engine + planner tests. Pure unittest (no DB / network):
    python -m unittest discover -s trips/tests -t .
or  python manage.py test
"""
import unittest
from datetime import datetime

from trips.hos import D, OFF, ON, SB, HOSPlanner, Leg, validate_plan
from trips.planner import build_trip_plan


def run(cycle, to_pickup, to_dropoff):
    """to_pickup / to_dropoff = (miles, minutes)."""
    p = HOSPlanner(cycle)
    return p.plan(Leg(*to_pickup, "A", "B"), Leg(*to_dropoff, "B", "C"))


def kinds(plan):
    return [s.kind for s in plan.segments]


class HOSRulesTest(unittest.TestCase):
    def test_short_trip_no_rest(self):
        plan = run(0, (100, 120), (300, 360))
        self.assertEqual(kinds(plan), ["drive", "pickup", "drive", "dropoff"])
        self.assertEqual(plan.total_minutes, 120 + 60 + 360 + 60)
        self.assertAlmostEqual(plan.total_miles, 400, places=1)

    def test_30_min_break_after_8_hours_driving(self):
        plan = run(0, (0, 0), (495, 540))     # 9 h straight
        self.assertEqual(kinds(plan), ["pickup", "drive", "break", "drive", "dropoff"])
        self.assertEqual(plan.segments[1].minutes, 480)
        self.assertEqual(plan.segments[2].status, OFF)
        self.assertEqual(plan.segments[2].minutes, 30)

    def test_pickup_counts_as_break(self):
        # 6 h + 1 h pickup + 6 h: the on-duty pickup satisfies the 30-min rule
        plan = run(0, (330, 360), (330, 360))
        self.assertNotIn("break", kinds(plan))

    def test_11_hour_limit_forces_10_hour_rest(self):
        plan = run(0, (0, 0), (660, 720))     # 12 h of driving
        drive_before_rest = 0
        for s in plan.segments:
            if s.kind == "rest":
                break
            if s.status == D:
                drive_before_rest += s.minutes
        self.assertIn("rest", kinds(plan))
        rest = next(s for s in plan.segments if s.kind == "rest")
        self.assertEqual(rest.status, SB)
        self.assertEqual(rest.minutes, 600)
        self.assertLessEqual(drive_before_rest, 660)

    def test_14_hour_window(self):
        # 5h drive, then 1h pickup ... window closes at 14h even with < 11h driving
        plan = run(0, (275, 300), (1100, 1200))
        self.assertEqual(validate_plan(plan.segments, 0), [])

    def test_fuel_every_1000_miles(self):
        plan = run(0, (0, 0), (2500, 2727))
        fuels = [s for s in plan.segments if s.kind == "fuel"]
        self.assertEqual(len(fuels), 2)
        for f in fuels:
            self.assertEqual(f.status, ON)
            self.assertEqual(f.minutes, 30)
        self.assertAlmostEqual(fuels[0].mile_start, 1000, delta=2)
        self.assertAlmostEqual(fuels[1].mile_start, 2000, delta=3)  # fuels at or just before each 1,000 mi
        self.assertEqual(validate_plan(plan.segments, 0), [])

    def test_cycle_limit_triggers_34_hour_restart(self):
        plan = run(65, (0, 0), (1100, 1200))
        self.assertIn("restart", kinds(plan))
        restart = next(s for s in plan.segments if s.kind == "restart")
        self.assertEqual(restart.minutes, 34 * 60)
        # only 5 h of cycle left (minus 1 h pickup = 4 h of driving) before restart
        driving_before = sum(s.minutes for s in plan.segments[: plan.segments.index(restart)]
                             if s.status == D)
        self.assertEqual(driving_before, 4 * 60)
        self.assertEqual(validate_plan(plan.segments, 65), [])

    def test_full_cycle_restarts_before_driving(self):
        plan = run(70, (50, 60), (50, 60))
        self.assertEqual(plan.segments[0].kind, "restart")

    def test_rejects_invalid_cycle(self):
        with self.assertRaises(ValueError):
            HOSPlanner(71)

    def test_long_haul_is_compliant_for_many_inputs(self):
        for cycle in (0, 12.5, 33, 50, 61, 69.5):
            for miles in (150, 640, 1300, 2800):
                plan = run(cycle, (miles * 0.2, round(miles * 0.2 / 52 * 60)),
                           (miles, round(miles / 52 * 60)))
                self.assertEqual(validate_plan(plan.segments, cycle), [], (cycle, miles))
                total = sum(s.minutes for s in plan.segments)
                self.assertEqual(total, plan.total_minutes)


class PlannerOutputTest(unittest.TestCase):
    places = {
        "current": {"label": "Dallas, TX", "lat": 32.78, "lon": -96.80},
        "pickup": {"label": "Oklahoma City, OK", "lat": 35.47, "lon": -97.52},
        "dropoff": {"label": "Los Angeles, CA", "lat": 34.05, "lon": -118.24},
    }
    route = {
        "geometry": [[32.78, -96.80], [34.0, -97.1], [35.47, -97.52], [35.2, -106.6], [34.05, -118.24]],
        "legs": [{"miles": 206, "minutes": 225}, {"miles": 1330, "minutes": 1450}],
        "leg_breaks": [0, 2],
        "source": "test",
    }

    def build(self, cycle=10, start=datetime(2026, 11, 13, 6, 0)):
        return build_trip_plan(places=self.places, route=self.route, cycle_used_hours=cycle,
                               start_time=start, reverse_geocode=lambda la, lo: "Somewhere, NM")

    def test_each_log_day_covers_24_hours(self):
        out = self.build()
        self.assertGreaterEqual(len(out["days"]), 2)
        for day in out["days"]:
            self.assertEqual(sum(day["totals_minutes"].values()), 1440)
            self.assertEqual(day["entries"][0]["start"], 0)
            self.assertEqual(day["entries"][-1]["end"], 1440)
            for a, b in zip(day["entries"], day["entries"][1:]):
                self.assertEqual(a["end"], b["start"])
                self.assertNotEqual(a["status"], b["status"])

    def test_daily_miles_add_up(self):
        out = self.build()
        self.assertAlmostEqual(sum(d["total_miles"] for d in out["days"]),
                               out["summary"]["total_miles"], delta=0.5)

    def test_first_day_starts_off_duty_until_start(self):
        out = self.build()
        first = out["days"][0]["entries"][0]
        self.assertEqual(first["status"], OFF)
        self.assertEqual(first["end"], 6 * 60)

    def test_stops_and_summary(self):
        out = self.build()
        types = [s["type"] for s in out["stops"]]
        self.assertEqual(types[0], "start")
        self.assertIn("pickup", types)
        self.assertEqual(types[-1], "dropoff")
        self.assertIn("fuel", types)
        self.assertTrue(out["summary"]["compliant"])
        pickup = next(s for s in out["stops"] if s["type"] == "pickup")
        self.assertEqual(pickup["location"], "Oklahoma City, OK")

    def test_recap_cycle_hours(self):
        out = self.build(cycle=10)
        last = out["days"][-1]
        self.assertAlmostEqual(last["cycle_used_end_hours"], out["summary"]["cycle_used_end_hours"], places=1)


if __name__ == "__main__":
    unittest.main()
