from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import TripCalculation


@admin.register(TripCalculation)
class TripCalculationAdmin(admin.ModelAdmin):
    """Admin interface for TripCalculation model."""

    list_display: list[str] = [
        "id",
        "current_location",
        "pickup_location",
        "dropoff_location",
        "status",
        "total_distance",
        "total_driving_time",
        "created_at",
    ]

    list_filter: list[str] = [
        "status",
        "created_at",
    ]

    search_fields: list[str] = [
        "current_location",
        "pickup_location",
        "dropoff_location",
    ]

    readonly_fields: list[str] = [
        "created_at",
        "updated_at",
        "total_distance",
        "total_driving_time",
        "total_trip_time",
        "route_data",
        "logs_data",
        "coordinates",
    ]

    fieldsets: list[tuple] = [
        (
            "Trip Information",
            {
                "fields": [
                    "current_location",
                    "pickup_location",
                    "dropoff_location",
                    "current_cycle_used",
                ]
            },
        ),
        (
            "Results",
            {
                "fields": [
                    "total_distance",
                    "total_driving_time",
                    "total_trip_time",
                    "route_data",
                    "logs_data",
                    "coordinates",
                ]
            },
        ),
        (
            "Status",
            {
                "fields": [
                    "status",
                    "error_message",
                ]
            },
        ),
        (
            "Timestamps",
            {
                "fields": [
                    "created_at",
                    "updated_at",
                ]
            },
        ),
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset."""
        return super().get_queryset(request).select_related()
