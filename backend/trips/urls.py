from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health),
    path("geocode/", views.geocode),
    path("reverse/", views.reverse),
    path("plan-trip/", views.plan_trip),
]
