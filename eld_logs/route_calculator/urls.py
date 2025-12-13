from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TripCalculationViewSet

router = DefaultRouter()
router.register(r"trips", TripCalculationViewSet, basename="trip")

urlpatterns = [
    path("", include(router.urls)),
]
