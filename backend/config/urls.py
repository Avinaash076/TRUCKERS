from django.urls import path
from routing import views
urlpatterns = [path("api/v1/health/", views.health), path("api/v1/geocode/", views.geocode), path("api/v1/assess/", views.assess), path("api/v1/corridor/", views.corridor)]
