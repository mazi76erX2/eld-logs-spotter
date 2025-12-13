from django.db import models
from typing import Any


class TripCalculation(models.Model):
    """Model to store trip calculation data and results."""

    class JobStatus(models.TextChoices):
        """Job status choices."""

        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    current_location = models.CharField(max_length=255)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    current_cycle_used = models.FloatField()
    total_distance = models.FloatField(null=True, blank=True)
    total_driving_time = models.FloatField(null=True, blank=True)
    total_trip_time = models.FloatField(null=True, blank=True)
    route_data = models.JSONField(null=True, blank=True)
    logs_data = models.JSONField(null=True, blank=True)
    coordinates = models.JSONField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=JobStatus.choices, default=JobStatus.PENDING
    )
    error_message = models.TextField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Trip Calculation"
        verbose_name_plural = "Trip Calculations"
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"Trip {self.id}: {self.current_location} -> {self.dropoff_location}"

    @property
    def is_completed(self) -> bool:
        """Check if trip calculation is completed."""
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        """Check if trip calculation failed."""
        return self.status == "failed"

    def get_route_segments(self) -> list[dict[str, Any]]:
        """Get route segments from route_data."""
        if self.route_data and isinstance(self.route_data, dict):
            return self.route_data.get("segments", [])
        return []

    def get_daily_logs(self) -> list[dict[str, Any]]:
        """Get daily logs."""
        if self.logs_data and isinstance(self.logs_data, list):
            return self.logs_data
        return []
