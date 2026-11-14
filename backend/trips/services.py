"""
Free map services (no API keys):
  * Photon (komoot) for search-as-you-type and reverse geocoding  - OpenStreetMap data
  * Nominatim as geocoding fallback                                 - OpenStreetMap data
  * OSRM public server for driving routes                           - OpenStreetMap data
"""
from __future__ import annotations

import logging
from typing import List, Optional

import requests
from django.conf import settings

from .planner import haversine_miles

log = logging.getLogger(__name__)

UA = {"User-Agent": "SpotterELDPlanner/1.0 (trip planning demo)"}
METERS_PER_MILE = 1609.344

US_STATES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA",
    "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}


class RoutingError(Exception):
    pass


def _photon_label(p: dict) -> str:
    name = p.get("name") or ""
    city = p.get("city") or p.get("town") or p.get("village") or p.get("county") or ""
    state = p.get("state") or ""
    state = US_STATES.get(state, state)
    parts = []
    for part in (name, city, state):
        if part and part not in parts:
            parts.append(part)
    country = p.get("countrycode", "")
    if country and country.upper() != "US" and p.get("country"):
        parts.append(p["country"])
    return ", ".join(parts)


def search_places(query: str, limit: int = 6) -> List[dict]:
    """Search-as-you-type suggestions (biased to North America)."""
    query = (query or "").strip()
    if len(query) < 2:
        return []
    try:
        r = requests.get(
            "https://photon.komoot.io/api/",
            params={"q": query, "limit": limit, "lang": "en", "lat": 39.5, "lon": -98.35},
            headers=UA, timeout=6,
        )
        r.raise_for_status()
        out = []
        for f in r.json().get("features", []):
            lon, lat = f["geometry"]["coordinates"]
            label = _photon_label(f.get("properties", {}))
            if label and not any(o["label"] == label for o in out):
                out.append({"label": label, "lat": lat, "lon": lon})
        if out:
            return out
    except Exception as exc:  # pragma: no cover - network
        log.warning("Photon search failed: %s", exc)
    return _nominatim_search(query, limit)


def _nominatim_search(query: str, limit: int) -> List[dict]:
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "jsonv2", "limit": limit, "addressdetails": 1},
            headers=UA, timeout=8,
        )
        r.raise_for_status()
        out = []
        for item in r.json():
            a = item.get("address", {})
            city = a.get("city") or a.get("town") or a.get("village") or a.get("county") or ""
            state = US_STATES.get(a.get("state", ""), a.get("state", ""))
            label = ", ".join(x for x in [city, state] if x) or item.get("display_name", "")
            out.append({"label": label, "lat": float(item["lat"]), "lon": float(item["lon"])})
        return out
    except Exception as exc:  # pragma: no cover - network
        log.warning("Nominatim search failed: %s", exc)
        return []


def geocode(query: str) -> Optional[dict]:
    results = search_places(query, limit=1)
    return results[0] if results else None


def reverse_geocode(lat: float, lon: float) -> Optional[str]:
    """'City, ST' for a coordinate - used for the log-sheet remarks."""
    try:
        r = requests.get(
            "https://photon.komoot.io/reverse",
            params={"lat": lat, "lon": lon, "lang": "en", "limit": 1},
            headers=UA, timeout=5,
        )
        r.raise_for_status()
        feats = r.json().get("features", [])
        if feats:
            p = feats[0]["properties"]
            city = p.get("city") or p.get("town") or p.get("village") or p.get("county") or p.get("name")
            state = US_STATES.get(p.get("state", ""), p.get("state", ""))
            label = ", ".join(x for x in [city, state] if x)
            if label:
                return label
    except Exception as exc:  # pragma: no cover - network
        log.info("Reverse geocode failed: %s", exc)
    return None


def get_route(points: List[dict]) -> dict:
    """Route current -> pickup -> dropoff. Returns geometry as [lat, lon] pairs,
    miles/minutes per leg and the geometry index where leg 2 begins."""
    coords = ";".join(f"{p['lon']:.6f},{p['lat']:.6f}" for p in points)
    base = getattr(settings, "OSRM_URL", "https://router.project-osrm.org")
    try:
        r = requests.get(
            f"{base}/route/v1/driving/{coords}",
            params={"overview": "full", "geometries": "geojson", "steps": "false"},
            headers=UA, timeout=15,
        )
        data = r.json()
        if data.get("code") != "Ok":
            raise RoutingError(data.get("message") or "No drivable route found between these locations.")
        route = data["routes"][0]
        geometry = [[lat, lon] for lon, lat in route["geometry"]["coordinates"]]
        legs = []
        max_mph = float(getattr(settings, "TRUCK_MAX_AVG_MPH", 55))
        for leg in route["legs"]:
            miles = leg["distance"] / METERS_PER_MILE
            minutes = leg["duration"] / 60
            # OSRM's profile is for cars; cap the average speed at a realistic
            # truck speed so drive times are not over-optimistic.
            if miles > 0:
                minutes = max(minutes, miles / max_mph * 60)
            legs.append({"miles": round(miles, 2), "minutes": round(minutes)})
        # index of the geometry vertex closest to the pickup = start of leg 2
        pk = (points[1]["lat"], points[1]["lon"])
        frac = legs[0]["miles"] / max(legs[0]["miles"] + legs[1]["miles"], 1e-9)
        guess = int(frac * (len(geometry) - 1))
        lo, hi = max(0, guess - len(geometry) // 4), min(len(geometry), guess + len(geometry) // 4 + 1)
        brk = min(range(lo, hi), key=lambda i: haversine_miles(pk, tuple(geometry[i]))) if hi > lo else guess
        return {"geometry": geometry, "legs": legs, "leg_breaks": [0, brk], "source": "osrm"}
    except RoutingError:
        raise
    except Exception as exc:  # pragma: no cover - network
        log.warning("OSRM failed, falling back to estimate: %s", exc)
        return estimate_route(points)


def estimate_route(points: List[dict]) -> dict:
    """Offline fallback: great-circle distance x 1.2 road factor at 50 mph."""
    legs, geometry = [], []
    for a, b in zip(points, points[1:]):
        miles = haversine_miles((a["lat"], a["lon"]), (b["lat"], b["lon"])) * 1.2
        legs.append({"miles": round(miles, 2), "minutes": round(miles / 50 * 60)})
    geometry = [[p["lat"], p["lon"]] for p in points]
    return {"geometry": geometry, "legs": legs, "leg_breaks": [0, 1], "source": "estimate"}
