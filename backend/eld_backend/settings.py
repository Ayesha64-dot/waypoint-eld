import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "*").split(",")

# Stateless API: no database, auth or admin needed.
INSTALLED_APPS = ["trips"]
MIDDLEWARE = [
    "eld_backend.cors.SimpleCorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]
ROOT_URLCONF = "eld_backend.urls"
WSGI_APPLICATION = "eld_backend.wsgi.application"
DATABASES = {}
TEMPLATES = []
USE_TZ = False
LANGUAGE_CODE = "en-us"
STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Map services (all free, no keys)
OSRM_URL = os.environ.get("OSRM_URL", "https://router.project-osrm.org")
TRUCK_MAX_AVG_MPH = float(os.environ.get("TRUCK_MAX_AVG_MPH", "55"))

LOGGING = {
    "version": 1,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
