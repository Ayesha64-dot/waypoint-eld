"""
Turns a routed trip + HOS simulation into the API payload the frontend renders:
route geometry, stops for the map, and one filled-in log sheet per calendar day.

Framework-free: networking is injected (route data + reverse geocoder), which
keeps this module fully unit-testable.
"""
from __future__ import annotations

import bisect
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .hos import (CYCLE_LIMIT_MINUTES, D, Leg, OFF, ON, SB, HOSPlanner,
                  RESTART_MINUTES, Segment, validate_plan)

DAY = 1440
STATUS_ORDER = [OFF, SB, D, ON]
STATUS_LABEL = {OFF: "Off Duty", SB: "Sleeper Berth", D: "Driving", ON: "On Duty (not driving)"}
KIND_LABEL = {
    "drive": "Driving", "pickup": "Pickup", "dropoff": "Drop-off", "fuel": "Fuel stop",
    "break": "30-min break", "rest": "10-hr rest", "restart": "34-hr restart",
    "start": "Start", "end": "Trip complete",
}

LatLon = Tuple[float, float]


# --------------------------------------------------------------------- geometry
def haversine_miles(a: LatLon, b: LatLon) -> float:
    r = 3958.7613
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


class RouteLine:
    """Find the coordinate at a given trip mile by walking the polyline."""

    def __init__(self, coords: Sequence[LatLon], leg_miles: Sequence[float],
                 leg_breaks: Sequence[int]):
        self.coords = list(coords)
        self.cum = [0.0]
        for i in range(1, len(self.coords)):
            self.cum.append(self.cum[-1] + haversine_miles(self.coords[i - 1], self.coords[i]))
        self.leg_miles = list(leg_miles)
        # index in coords where each leg starts (0 and the pickup vertex)
        self.leg_breaks = list(leg_breaks)

    def point_at(self, mile: float) -> LatLon:
        if len(self.coords) == 1:
            return self.coords[0]
        # map the routed-mile figure onto the geometry, leg by leg, so stops
        # are always placed on the correct side of the pickup
        leg = 0 if mile <= self.leg_miles[0] or len(self.leg_miles) == 1 else 1
        leg_start_mile = 0.0 if leg == 0 else self.leg_miles[0]
        frac = 0.0 if self.leg_miles[leg] <= 0 else (mile - leg_start_mile) / self.leg_miles[leg]
        frac = min(max(frac, 0.0), 1.0)
        i0 = self.leg_breaks[leg]
        i1 = self.leg_breaks[leg + 1] if leg + 1 < len(self.leg_breaks) else len(self.coords) - 1
        g0, g1 = self.cum[i0], self.cum[i1]
        target = g0 + frac * (g1 - g0)
        j = bisect.bisect_left(self.cum, target, lo=i0, hi=max(i1, i0 + 1))
        j = min(max(j, 1), len(self.coords) - 1)
        seg = self.cum[j] - self.cum[j - 1]
        t = 0.0 if seg <= 0 else (target - self.cum[j - 1]) / seg
        a, b = self.coords[j - 1], self.coords[j]
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def simplify(coords: Sequence[LatLon], max_points: int = 1500) -> List[List[float]]:
    if len(coords) <= max_points:
        return [[round(a, 5), round(b, 5)] for a, b in coords]
    step = len(coords) / max_points
    out = [coords[int(i * step)] for i in range(max_points)]
    out.append(coords[-1])
    return [[round(a, 5), round(b, 5)] for a, b in out]


def fmt_hhmm(minute_of_day: int) -> str:
    minute_of_day = int(round(minute_of_day))
    if minute_of_day >= DAY:
        return "24:00"
    return f"{minute_of_day // 60:02d}:{minute_of_day % 60:02d}"


def fmt_duration(minutes: int) -> str:
    h, m = divmod(int(round(minutes)), 60)
    if h and m:
        return f"{h}h {m:02d}m"
    return f"{h}h" if h else f"{m}m"


# ------------------------------------------------------------------- main entry
def build_trip_plan(
    *,
    places: Dict[str, dict],               # current / pickup / dropoff -> {label, lat, lon}
    route: dict,                           # {geometry:[[lat,lon]], legs:[{miles,minutes}], leg_breaks, source}
    cycle_used_hours: float,
    start_time: datetime,
    reverse_geocode: Optional[Callable[[float, float], Optional[str]]] = None,
    log_info: Optional[dict] = None,
) -> dict:
    legs = route["legs"]
    to_pickup = Leg(miles=legs[0]["miles"], minutes=int(round(legs[0]["minutes"])),
                    origin=places["current"]["label"], destination=places["pickup"]["label"])
    to_dropoff = Leg(miles=legs[1]["miles"], minutes=int(round(legs[1]["minutes"])),
                     origin=places["pickup"]["label"], destination=places["dropoff"]["label"])

    planner = HOSPlanner(cycle_used_hours)
    plan = planner.plan(to_pickup, to_dropoff)
    segments = plan.segments
    violations = validate_plan(segments, cycle_used_hours)

    line = RouteLine(
        [tuple(c) for c in route["geometry"]],
        [to_pickup.miles, to_dropoff.miles],
        route.get("leg_breaks") or [0, 0],
    )

    # ---- resolve a human-readable location for every duty-status change
    def short(label: str) -> str:
        parts = [p.strip() for p in label.split(",") if p.strip()]
        return ", ".join(parts[:2]) if parts else label

    fixed = {
        "current": short(places["current"]["label"]),
        "pickup": short(places["pickup"]["label"]),
        "dropoff": short(places["dropoff"]["label"]),
    }

    def seg_point(seg: Segment) -> LatLon:
        if seg.kind == "pickup":
            return (places["pickup"]["lat"], places["pickup"]["lon"])
        if seg.kind == "dropoff":
            return (places["dropoff"]["lat"], places["dropoff"]["lon"])
        if seg.mile_start <= 0.01:
            return (places["current"]["lat"], places["current"]["lon"])
        return line.point_at(seg.mile_start)

    points = [seg_point(s) for s in segments]
    labels: List[Optional[str]] = [None] * len(segments)
    to_lookup = []
    for i, seg in enumerate(segments):
        if seg.kind == "pickup":
            labels[i] = fixed["pickup"]
        elif seg.kind == "dropoff":
            labels[i] = fixed["dropoff"]
        elif seg.mile_start <= 0.01:
            labels[i] = fixed["current"]
        elif seg.kind != "drive":
            to_lookup.append(i)
    # driving segments that start right after a stop share the stop's location
    if reverse_geocode and to_lookup:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda i: _safe(reverse_geocode, *points[i]), to_lookup))
        for i, name in zip(to_lookup, results):
            labels[i] = name
    for i, seg in enumerate(segments):
        if labels[i] is None and seg.kind != "drive":
            labels[i] = f"Mile {seg.mile_start:,.0f} ({points[i][0]:.3f}, {points[i][1]:.3f})"
    for i, seg in enumerate(segments):
        if labels[i] is None:   # a drive segment that follows a stop
            labels[i] = labels[i - 1] if i > 0 else fixed["current"]

    # ---- absolute timeline (minutes since midnight of the first log day)
    day0 = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    offset = (start_time - day0).seconds // 60
    end_abs = offset + plan.total_minutes
    num_days = max(1, math.ceil(end_abs / DAY))

    timeline = []
    if offset > 0:
        timeline.append(dict(start=0, end=offset, status=OFF, kind="pre", note="Off duty",
                             mile_start=0.0, mile_end=0.0, location=fixed["current"]))
    for seg, label in zip(segments, labels):
        timeline.append(dict(start=offset + seg.start, end=offset + seg.end, status=seg.status,
                             kind=seg.kind, note=seg.note, mile_start=seg.mile_start,
                             mile_end=seg.mile_end, location=label))
    if end_abs < num_days * DAY:
        timeline.append(dict(start=end_abs, end=num_days * DAY, status=OFF, kind="end",
                             note="Off duty - trip complete", mile_start=plan.total_miles,
                             mile_end=plan.total_miles, location=fixed["dropoff"]))

    # ---- cycle hours at each day boundary (for the recap section)
    cycle = int(round(cycle_used_hours * 60))
    cycle_at: Dict[int, int] = {}
    boundaries = [d * DAY for d in range(1, num_days + 1)]
    bi = 0
    for item in timeline:
        while bi < len(boundaries) and boundaries[bi] <= item["start"]:
            cycle_at[bi] = cycle
            bi += 1
        dur = item["end"] - item["start"]
        if item["status"] in (D, ON):
            while bi < len(boundaries) and boundaries[bi] < item["end"]:
                cycle_at[bi] = cycle + (boundaries[bi] - item["start"])
                bi += 1
            cycle += dur
        elif item["kind"] == "restart" and dur >= RESTART_MINUTES:
            while bi < len(boundaries) and boundaries[bi] < item["end"]:
                cycle_at[bi] = cycle
                bi += 1
            cycle = 0
    while bi < len(boundaries):
        cycle_at[bi] = cycle
        bi += 1

    # ---- daily log sheets
    info = log_info or {}
    days = []
    for d in range(num_days):
        lo, hi = d * DAY, (d + 1) * DAY
        entries, remarks = [], []
        miles_today = 0.0
        totals = {k: 0 for k in STATUS_ORDER}
        for item in timeline:
            s, e = max(item["start"], lo), min(item["end"], hi)
            if e <= s:
                continue
            totals[item["status"]] += e - s
            if item["status"] == D:
                span = item["end"] - item["start"]
                miles_today += (item["mile_end"] - item["mile_start"]) * (e - s) / span
            if entries and entries[-1]["status"] == item["status"] and entries[-1]["end"] == s - lo:
                entries[-1]["end"] = e - lo
            else:
                entries.append(dict(status=item["status"], start=s - lo, end=e - lo))
            if lo <= item["start"] < hi and item["kind"] != "pre":
                remarks.append(dict(
                    time=fmt_hhmm(item["start"] - lo), minute=item["start"] - lo,
                    status=item["status"], location=item["location"],
                    note=KIND_LABEL.get(item["kind"], item["note"]) if item["kind"] != "drive" else "Driving",
                ))
        first = next(i for i in timeline if i["end"] > lo)
        last = [i for i in timeline if i["start"] < hi][-1]
        on_duty_today = totals[D] + totals[ON]
        cycle_end = cycle_at.get(d, cycle)
        date = (day0 + timedelta(days=d)).date()
        days.append(dict(
            day=d + 1,
            date=date.isoformat(),
            date_label=date.strftime("%a, %b %d %Y"),
            from_location=first["location"],
            to_location=last["location"],
            total_miles=round(miles_today, 1),
            entries=entries,
            remarks=remarks,
            totals_minutes=totals,
            totals_hours={k: round(v / 60, 2) for k, v in totals.items()},
            on_duty_today_hours=round(on_duty_today / 60, 2),
            cycle_used_end_hours=round(cycle_end / 60, 2),
            cycle_available_hours=round(max(0, CYCLE_LIMIT_MINUTES - cycle_end) / 60, 2),
            driver_name=info.get("driver_name", ""),
            carrier_name=info.get("carrier_name", ""),
            truck_number=info.get("truck_number", ""),
            main_office=info.get("main_office", ""),
            co_driver=info.get("co_driver", ""),
            shipping_doc=info.get("shipping_doc", ""),
        ))

    # ---- stops for the map + itinerary
    stops = [dict(
        type="start", label=KIND_LABEL["start"], location=fixed["current"],
        lat=places["current"]["lat"], lon=places["current"]["lon"],
        arrival=start_time.isoformat(timespec="minutes"), duration_minutes=0,
        duration_label="", mile=0.0, status=D,
    )]
    for seg, label, pt in zip(segments, labels, points):
        if seg.kind == "drive":
            continue
        stops.append(dict(
            type=seg.kind, label=KIND_LABEL[seg.kind], location=label,
            lat=round(pt[0], 5), lon=round(pt[1], 5),
            arrival=(start_time + timedelta(minutes=seg.start)).isoformat(timespec="minutes"),
            departure=(start_time + timedelta(minutes=seg.end)).isoformat(timespec="minutes"),
            duration_minutes=seg.minutes, duration_label=fmt_duration(seg.minutes),
            mile=round(seg.mile_start, 1), status=seg.status, note=seg.note,
        ))

    total_drive = sum(s.minutes for s in segments if s.status == D)
    total_on = sum(s.minutes for s in segments if s.status == ON)
    count = lambda k: sum(1 for s in segments if s.kind == k)
    end_time = start_time + timedelta(minutes=plan.total_minutes)

    return dict(
        summary=dict(
            total_miles=plan.total_miles,
            miles_to_pickup=round(to_pickup.miles, 1),
            miles_to_dropoff=round(to_dropoff.miles, 1),
            driving_minutes=total_drive,
            driving_label=fmt_duration(total_drive),
            on_duty_minutes=total_on,
            trip_minutes=plan.total_minutes,
            trip_label=fmt_duration(plan.total_minutes),
            start_time=start_time.isoformat(timespec="minutes"),
            end_time=end_time.isoformat(timespec="minutes"),
            log_days=num_days,
            fuel_stops=count("fuel"), breaks=count("break"),
            rests=count("rest"), restarts=count("restart"),
            cycle_used_start_hours=cycle_used_hours,
            cycle_used_end_hours=round(plan.cycle_used_at_end / 60, 2),
            compliant=not violations,
            violations=violations,
            route_source=route.get("source", "osrm"),
        ),
        places=places,
        route=dict(geometry=simplify(route["geometry"]), legs=legs),
        stops=stops,
        timeline=[dict(
            start=(start_time + timedelta(minutes=s.start)).isoformat(timespec="minutes"),
            end=(start_time + timedelta(minutes=s.end)).isoformat(timespec="minutes"),
            status=s.status, kind=s.kind, label=KIND_LABEL[s.kind], minutes=s.minutes,
            duration_label=fmt_duration(s.minutes), location=label,
            miles=round(s.mile_end - s.mile_start, 1),
        ) for s, label in zip(segments, labels)],
        days=days,
    )


def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception:  # network hiccups must never break the plan
        return None
