"""
Hours-of-Service (HOS) trip simulator for a property-carrying CMV driver.

Pure Python, no Django imports, so it can be unit-tested in isolation.
All time is tracked in integer minutes from the moment the trip starts.

FMCSA rules modelled (49 CFR 395.3, property-carrying):
  * 11-hour driving limit   - max 11 h driving after 10 consecutive hours off duty
  * 14-hour window          - no driving after the 14th hour since coming on duty
  * 30-minute break         - required after 8 cumulative hours of driving; any
                              30 consecutive minutes not driving satisfies it
                              (off duty, sleeper, or on-duty such as fueling)
  * 70-hour / 8-day limit   - no driving after 70 h on duty; a 34-hour restart
                              resets the cycle to zero
Trip assumptions (from the brief):
  * fuel at least every 1,000 miles (30 min, on duty not driving)
  * 1 hour on duty for pickup and 1 hour for drop-off
  * no adverse driving conditions (no 2-hour extension)
  * 10-hour resets are logged in the sleeper berth, short breaks as off duty
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

OFF = "OFF"   # Off duty
SB = "SB"     # Sleeper berth
D = "D"       # Driving
ON = "ON"     # On duty, not driving

MAX_DRIVING_PER_SHIFT = 11 * 60
MAX_DUTY_WINDOW = 14 * 60
DRIVING_BEFORE_BREAK = 8 * 60
BREAK_MINUTES = 30
DAILY_RESET_MINUTES = 10 * 60
CYCLE_LIMIT_MINUTES = 70 * 60
RESTART_MINUTES = 34 * 60
FUEL_INTERVAL_MILES = 1000.0
FUEL_MINUTES = 30
PICKUP_MINUTES = 60
DROPOFF_MINUTES = 60


@dataclass
class Leg:
    """One routed leg (current -> pickup, or pickup -> dropoff)."""
    miles: float
    minutes: int
    origin: str = ""
    destination: str = ""


@dataclass
class Segment:
    start: int            # minutes from trip start
    end: int
    status: str           # OFF / SB / D / ON
    kind: str             # drive, pickup, dropoff, fuel, break, rest, restart
    note: str
    mile_start: float
    mile_end: float
    leg_index: int = 0

    @property
    def minutes(self) -> int:
        return self.end - self.start


@dataclass
class HOSState:
    t: int = 0
    cycle_used: int = 0
    shift_start: Optional[int] = None
    driving_in_shift: int = 0
    driving_since_break: int = 0
    miles: float = 0.0
    miles_since_fuel: float = 0.0

    @property
    def window_used(self) -> int:
        return 0 if self.shift_start is None else self.t - self.shift_start


@dataclass
class TripPlan:
    segments: List[Segment] = field(default_factory=list)
    total_minutes: int = 0
    total_miles: float = 0.0
    cycle_used_at_end: int = 0


class HOSPlanner:
    def __init__(self, cycle_used_hours: float):
        if cycle_used_hours < 0 or cycle_used_hours > 70:
            raise ValueError("Current cycle used must be between 0 and 70 hours.")
        self.s = HOSState(cycle_used=int(round(cycle_used_hours * 60)))
        self.segments: List[Segment] = []
        self.leg_index = 0

    # ------------------------------------------------------------------ core
    def _log(self, status: str, minutes: int, kind: str, note: str, miles: float = 0.0):
        if minutes <= 0:
            return
        s = self.s
        seg = Segment(
            start=s.t, end=s.t + minutes, status=status, kind=kind, note=note,
            mile_start=round(s.miles, 3), mile_end=round(s.miles + miles, 3),
            leg_index=self.leg_index,
        )
        # merge back-to-back driving blocks so the log shows one continuous line
        prev = self.segments[-1] if self.segments else None
        if prev and prev.kind == kind == "drive" and prev.end == seg.start:
            prev.end = seg.end
            prev.mile_end = seg.mile_end
        else:
            self.segments.append(seg)

        if status in (D, ON):
            if s.shift_start is None:
                s.shift_start = s.t
            s.cycle_used += minutes
        if status == D:
            s.driving_in_shift += minutes
            s.driving_since_break += minutes
        elif minutes >= BREAK_MINUTES:
            # any 30+ consecutive minutes not driving satisfies the break rule
            s.driving_since_break = 0

        s.t += minutes
        s.miles += miles
        s.miles_since_fuel += miles

    def _daily_reset(self):
        self._log(SB, DAILY_RESET_MINUTES, "rest", "10-hr off-duty reset (sleeper berth)")
        s = self.s
        s.shift_start = None
        s.driving_in_shift = 0
        s.driving_since_break = 0

    def _restart(self):
        self._log(OFF, RESTART_MINUTES, "restart", "34-hr restart (70-hr cycle reached)")
        s = self.s
        s.cycle_used = 0
        s.shift_start = None
        s.driving_in_shift = 0
        s.driving_since_break = 0

    def _break(self):
        self._log(OFF, BREAK_MINUTES, "break", "30-min break (8 hrs driving)")

    def _fuel(self):
        self._log(ON, FUEL_MINUTES, "fuel", "Fueling")
        self.s.miles_since_fuel = 0.0

    # --------------------------------------------------------------- actions
    def on_duty(self, kind: str, minutes: int, note: str):
        """Pickup / drop-off. On-duty work is legal past the 14th hour and past
        70 hours (those limits only restrict *driving*), so no rest is forced here;
        the next drive call will insert any required rest."""
        self._log(ON, minutes, kind, note)

    def drive(self, leg: Leg):
        s = self.s
        if leg.minutes <= 0 or leg.miles <= 0:
            return
        mpm = leg.miles / leg.minutes   # miles per minute for this leg
        remaining_min = leg.minutes
        remaining_miles = leg.miles

        guard = 0
        while remaining_min > 0:
            guard += 1
            if guard > 10_000:
                raise RuntimeError("HOS simulation did not converge")

            cycle_left = CYCLE_LIMIT_MINUTES - s.cycle_used
            if cycle_left <= 0:
                self._restart()
                continue
            if s.driving_in_shift >= MAX_DRIVING_PER_SHIFT or s.window_used >= MAX_DUTY_WINDOW:
                self._daily_reset()
                continue
            if s.driving_since_break >= DRIVING_BEFORE_BREAK:
                self._break()
                continue
            minutes_to_fuel = int((FUEL_INTERVAL_MILES - s.miles_since_fuel) / mpm + 1e-9)
            if minutes_to_fuel <= 0:
                self._fuel()
                continue

            chunk = min(
                remaining_min,
                MAX_DRIVING_PER_SHIFT - s.driving_in_shift,
                MAX_DUTY_WINDOW - s.window_used,
                DRIVING_BEFORE_BREAK - s.driving_since_break,
                cycle_left,
                minutes_to_fuel,
            )
            miles = remaining_miles if chunk == remaining_min else chunk * mpm
            self._log(D, chunk, "drive", f"Driving to {leg.destination}".strip(), miles)
            remaining_min -= chunk
            remaining_miles -= miles

    # ------------------------------------------------------------------ trip
    def plan(self, to_pickup: Leg, to_dropoff: Leg) -> TripPlan:
        self.leg_index = 0
        self.drive(to_pickup)
        self.on_duty("pickup", PICKUP_MINUTES, "Pickup - loading")
        self.leg_index = 1
        self.drive(to_dropoff)
        self.on_duty("dropoff", DROPOFF_MINUTES, "Drop-off - unloading")
        return TripPlan(
            segments=self.segments,
            total_minutes=self.s.t,
            total_miles=round(self.s.miles, 1),
            cycle_used_at_end=self.s.cycle_used,
        )


def validate_plan(segments: List[Segment], cycle_used_hours: float) -> List[str]:
    """Independent compliance checker used by the tests (and exposed in the API
    response) - re-walks the timeline and reports any HOS violation."""
    problems: List[str] = []
    cycle = int(round(cycle_used_hours * 60))
    shift_start = None
    drive_shift = 0
    since_break = 0
    nondrive_run = 0
    miles_since_fuel = 0.0
    off_run = 0
    for seg in segments:
        m = seg.minutes
        if seg.status in (OFF, SB):
            off_run += m
            nondrive_run += m
            if off_run >= RESTART_MINUTES:
                cycle = 0
            if off_run >= DAILY_RESET_MINUTES:
                shift_start, drive_shift, since_break = None, 0, 0
            if nondrive_run >= BREAK_MINUTES:
                since_break = 0
            continue
        off_run = 0
        if shift_start is None:
            shift_start = seg.start
        if seg.status == ON:
            nondrive_run += m
            if nondrive_run >= BREAK_MINUTES:
                since_break = 0
            if seg.kind == "fuel":
                miles_since_fuel = 0.0
            cycle += m
            continue
        # driving
        nondrive_run = 0
        if seg.end - shift_start > MAX_DUTY_WINDOW:
            problems.append(f"Driving past 14-hr window at minute {seg.start}")
        drive_shift += m
        since_break += m
        cycle += m
        miles_since_fuel += seg.mile_end - seg.mile_start
        if drive_shift > MAX_DRIVING_PER_SHIFT:
            problems.append(f"More than 11 hrs driving in shift at minute {seg.start}")
        if since_break > DRIVING_BEFORE_BREAK:
            problems.append(f"Over 8 hrs driving without a 30-min break at minute {seg.start}")
        if cycle > CYCLE_LIMIT_MINUTES:
            problems.append(f"Driving beyond 70-hr cycle at minute {seg.start}")
        if miles_since_fuel > FUEL_INTERVAL_MILES + 0.5:
            problems.append(f"Over 1,000 miles without fueling at minute {seg.start}")
    return problems
