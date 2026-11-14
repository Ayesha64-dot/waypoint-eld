import json
from datetime import datetime

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from . import services
from .planner import build_trip_plan

PLACE_KEYS = {
    "current": "current_location",
    "pickup": "pickup_location",
    "dropoff": "dropoff_location",
}


def _error(message, status=400, field=None):
    return JsonResponse({"error": message, "field": field}, status=status)


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})


@require_GET
def geocode(request):
    return JsonResponse({"results": services.search_places(request.GET.get("q", ""))})


def _resolve_place(value, field):
    """Accept {label, lat, lon} from the autocomplete or a plain text address."""
    if isinstance(value, dict) and value.get("lat") is not None and value.get("lon") is not None:
        try:
            return {"label": str(value.get("label") or f"{value['lat']}, {value['lon']}"),
                    "lat": float(value["lat"]), "lon": float(value["lon"])}, None
        except (TypeError, ValueError):
            return None, _error("Invalid coordinates.", field=field)
    text = value.get("label") if isinstance(value, dict) else value
    if not text or not str(text).strip():
        return None, _error("This location is required.", field=field)
    place = services.geocode(str(text))
    if not place:
        return None, _error(f'Could not find "{text}". Try a city and state.', field=field)
    return place, None


@require_GET
def reverse(request):
    try:
        lat, lon = float(request.GET["lat"]), float(request.GET["lon"])
    except (KeyError, ValueError):
        return _error("lat and lon are required.")
    label = services.reverse_geocode(lat, lon) or f"{lat:.4f}, {lon:.4f}"
    return JsonResponse({"label": label, "lat": lat, "lon": lon})


@csrf_exempt
@require_http_methods(["POST"])
def plan_trip(request):
    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _error("Request body must be JSON.")

    places = {}
    for key, field in PLACE_KEYS.items():
        place, err = _resolve_place(body.get(field), field)
        if err:
            return err
        places[key] = place

    try:
        cycle = float(body.get("current_cycle_used", 0))
    except (TypeError, ValueError):
        return _error("Current cycle used must be a number.", field="current_cycle_used")
    if not 0 <= cycle <= 70:
        return _error("Current cycle used must be between 0 and 70 hours.", field="current_cycle_used")

    start_raw = body.get("start_time")
    try:
        start = datetime.fromisoformat(start_raw) if start_raw else datetime.now()
    except ValueError:
        return _error("Start time must be ISO formatted (YYYY-MM-DDTHH:MM).", field="start_time")
    start = start.replace(tzinfo=None, second=0, microsecond=0)

    try:
        route = services.get_route([places["current"], places["pickup"], places["dropoff"]])
    except services.RoutingError as exc:
        return _error(str(exc), status=422)

    total = sum(l["miles"] for l in route["legs"])
    if total > 6000:
        return _error("That trip is longer than 6,000 miles - please choose locations on the same continent.", status=422)

    log_info = {k: str(body.get(k, ""))[:80] for k in
                ("driver_name", "carrier_name", "truck_number", "main_office", "co_driver", "shipping_doc")}

    plan = build_trip_plan(
        places=places, route=route, cycle_used_hours=cycle, start_time=start,
        reverse_geocode=services.reverse_geocode, log_info=log_info,
    )
    return JsonResponse(plan)
