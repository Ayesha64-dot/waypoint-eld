"""Tiny CORS middleware (avoids an extra dependency).
Allowed origins come from CORS_ALLOWED_ORIGINS (comma separated) or '*'."""
from django.conf import settings
from django.http import HttpResponse


class SimpleCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed = [o.strip() for o in settings.CORS_ALLOWED_ORIGINS if o.strip()]

    def __call__(self, request):
        if request.method == "OPTIONS":
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)
        origin = request.headers.get("Origin")
        if origin and ("*" in self.allowed or origin in self.allowed):
            response["Access-Control-Allow-Origin"] = origin
            response["Vary"] = "Origin"
            response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type"
            response["Access-Control-Max-Age"] = "86400"
        return response
