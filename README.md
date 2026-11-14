# Waypoint ELD: HOS Trip Planner & Log Generator

A full-stack app built with **Django + React**. You enter a trip, and it returns a route map with every required stop and rest, plus **filled-in, hand-drawn-style ELD daily log sheets** (one per calendar day).

**Inputs:** current location, pickup location, drop-off location, current cycle used (hrs), plus optional departure time and log-header fields
**Outputs:** route map (OpenStreetMap / OSRM), stop-by-stop itinerary, trip duty-status timeline, daily log sheets you can print or save as PDF

---

## Architecture

```
frontend/  React 18 + Vite + Leaflet       → deploy to Vercel (static)
backend/   Django 5 (stateless JSON API)   → deploy to Vercel (Python serverless) or Render
```

| Layer | What it does |
|---|---|
| `backend/trips/hos.py` | **The HOS engine.** A minute-by-minute simulator for a property-carrying driver. It has no Django dependency and is fully unit-tested. It also includes an independent `validate_plan()` compliance checker. |
| `backend/trips/planner.py` | Turns the simulation into the API payload. It places each stop on the route polyline, splits the timeline at midnight into daily logs, and computes per-day totals, miles, remarks and the 70-hr recap. |
| `backend/trips/services.py` | Free map services with no API keys: **Photon** for autocomplete and reverse geocoding, **Nominatim** as the geocoding fallback, and **OSRM** for driving routes. If OSRM is down, it falls back to an offline estimate. |
| `backend/trips/views.py` | `POST /api/plan-trip/`, `GET /api/geocode/?q=`, `GET /api/reverse/?lat=&lon=`, `GET /api/health/` |
| `frontend/src/components/LogSheet.jsx` | Draws the FMCSA-style log grid in SVG: 24-hour grid with 15-minute ticks, duty-status line, row totals, angled remarks with location at every status change, and the recap. |
| `frontend/src/components/RouteMap.jsx` | Leaflet map with CARTO/OSM tiles, the route line and colour-coded stop markers. Clicking an itinerary row flies the map to that stop. |

## HOS rules implemented (49 CFR 395.3, property-carrying, 70 hr / 8 day)

| Rule | Behaviour |
|---|---|
| 11-hour driving limit | After 11 h of driving, a **10-hr reset** is inserted (logged as Sleeper Berth) |
| 14-hour window | No driving after the 14th hour since coming on duty. On-duty work after that is allowed, because the rule only restricts driving. |
| 30-minute break | Required after 8 cumulative hours of driving. **Any 30 consecutive non-driving minutes count**, including the pickup hour or a fuel stop (2020 rule). |
| 70 hr / 8 day | When the cycle is used up, a **34-hr restart** (Off Duty) resets it to 0 |
| Fuel | A 30-min on-duty fuel stop at least every 1,000 miles |
| Pickup / drop-off | 1 h On Duty (not driving) each |
| Daily logs | Midnight-to-midnight. Off duty before departure on day 1 and after arrival on the last day. Every sheet totals 24:00. |

**Assumptions / simplifications** (stated in the UI too):
- The truck starts with a full tank.
- "Cycle used" is treated as hours already consumed. Hours dropping off the rolling 8-day window aren't recaptured, because the per-day history isn't provided. That makes the plan conservative.
- OSRM's car profile is capped at a **55 mph average** (`TRUCK_MAX_AVG_MPH`) so truck drive times are realistic.
- Times use the departure time entered, which is the home-terminal time.

## Run locally

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py test trips          # 15 HOS + planner tests
python manage.py runserver 8000

# frontend (new terminal)
cd frontend
cp .env.example .env                 # VITE_API_URL=http://localhost:8000
npm install
npm run dev                          # http://localhost:5173
```

## Deploy (Vercel, two projects from one repo)

1. Push this repo to GitHub.
2. **Backend:** in Vercel, choose *New Project*, import the repo and set **Root Directory = `backend`**. The framework preset is "Other", and `backend/vercel.json` routes everything to `api/index.py`. Add env vars:
   - `DJANGO_SECRET_KEY` = any long random string
   - `CORS_ALLOWED_ORIGINS` = `*` (or your frontend URL once you know it)

   Deploy, then check `https://<backend>.vercel.app/api/health/` returns `{"status":"ok"}`.
3. **Frontend:** choose *New Project* again with the same repo and set **Root Directory = `frontend`** (preset: Vite). Add env var `VITE_API_URL=https://<backend>.vercel.app`, then deploy.
4. Optional: set `CORS_ALLOWED_ORIGINS` on the backend to the exact frontend URL and redeploy.

*Alternative backend host:* `render.yaml` deploys the same Django app on Render with gunicorn.

## API example

```http
POST /api/plan-trip/
{
  "current_location":  {"label": "Dallas, TX", "lat": 32.7767, "lon": -96.797},
  "pickup_location":   "Oklahoma City, OK",          // plain text is geocoded server-side
  "dropoff_location":  {"label": "Los Angeles, CA", "lat": 34.0522, "lon": -118.2437},
  "current_cycle_used": 18,
  "start_time": "2026-11-13T07:00",
  "driver_name": "…", "carrier_name": "…", "truck_number": "…"
}
```

The response contains `summary`, `route.geometry`, `stops[]`, `timeline[]` and `days[]`. Each day has `entries`, `remarks`, `totals_minutes` and the recap fields.
