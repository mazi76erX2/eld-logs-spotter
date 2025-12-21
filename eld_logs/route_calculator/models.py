from typing import Any

from django.db import models


class TripCalculation(models.Model):
    """Model to store trip calculation data and results."""

    class JobStatus(models.TextChoices):
        """Job status choices."""

        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class MapStatus(models.TextChoices):
        """Map generation status choices."""

        NOT_STARTED = "not_started", "Not Started"
        GENERATING = "generating", "Generating"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    # Trip locations
    current_location = models.CharField(max_length=255)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    current_cycle_used = models.FloatField()

    # Calculated results
    total_distance = models.FloatField(null=True, blank=True)
    total_driving_time = models.FloatField(null=True, blank=True)
    total_trip_time = models.FloatField(null=True, blank=True)
    route_data = models.JSONField(null=True, blank=True)
    logs_data = models.JSONField(null=True, blank=True)
    coordinates = models.JSONField(null=True, blank=True)

    # Trip calculation status
    status = models.CharField(
        max_length=20,
        choices=JobStatus.choices,
        default=JobStatus.PENDING,
        db_index=True,
    )
    error_message = models.TextField(null=True, blank=True)

    progress = models.IntegerField(default=0)  # 0-100 for trip calculation
    map_status = models.CharField(
        max_length=20,
        choices=MapStatus.choices,
        default=MapStatus.NOT_STARTED,
        db_index=True,
    )
    map_progress = models.IntegerField(default=0)  # 0-100 for map generation
    map_error_message = models.TextField(null=True, blank=True)
    map_file = models.ImageField(
        upload_to="maps/%Y/%m/%d/",
        null=True,
        blank=True,
    )
    map_task_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)

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
            models.Index(fields=["map_status"]),
            models.Index(fields=["status", "map_status"]),
        ]

    def __str__(self) -> str:
        return f"Trip {self.id}: {self.current_location} -> {self.dropoff_location}"

    @property
    def is_completed(self) -> bool:
        """Check if trip calculation is completed."""
        return self.status == self.JobStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if trip calculation failed."""
        return self.status == self.JobStatus.FAILED

    @property
    def is_map_ready(self) -> bool:
        """Check if map is ready for download."""
        return (
            self.map_status == self.MapStatus.COMPLETED
            and bool(self.map_file)
            and self.map_file.name
        )

    @property
    def overall_progress(self) -> int:
        """
        Calculate overall progress combining trip calculation and map generation.
        Trip calculation: 0-70%
        Map generation: 70-100%
        """
        if self.status == self.JobStatus.FAILED:
            return 0

        trip_progress = min(self.progress, 100) * 0.7

        if self.map_status == self.MapStatus.NOT_STARTED:
            map_progress = 0
        elif self.map_status == self.MapStatus.GENERATING:
            map_progress = min(self.map_progress, 100) * 0.3
        elif self.map_status == self.MapStatus.COMPLETED:
            map_progress = 30
        else:
            map_progress = 0

        return int(trip_progress + map_progress)

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

    def update_progress(self, progress: int, status: str | None = None) -> None:
        """Update trip calculation progress."""
        self.progress = min(max(progress, 0), 100)
        if status:
            self.status = status
        self.save(update_fields=["progress", "status", "updated_at"])

    def update_map_progress(self, progress: int, status: str | None = None) -> None:
        """Update map generation progress."""
        self.map_progress = min(max(progress, 0), 100)
        if status:
            self.map_status = status
        self.save(update_fields=["map_progress", "map_status", "updated_at"])
