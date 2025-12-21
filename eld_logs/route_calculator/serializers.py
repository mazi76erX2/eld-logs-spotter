from rest_framework import serializers

from .models import TripCalculation


class TripCalculationSerializer(serializers.ModelSerializer):
    """Serializer for TripCalculation model."""

    is_completed = serializers.BooleanField(read_only=True)
    is_map_ready = serializers.BooleanField(read_only=True)
    overall_progress = serializers.IntegerField(read_only=True)
    map_url = serializers.SerializerMethodField()

    class Meta:
        model = TripCalculation
        fields = [
            "id",
            "created_at",
            "updated_at",
            "current_location",
            "pickup_location",
            "dropoff_location",
            "current_cycle_used",
            "total_distance",
            "total_driving_time",
            "total_trip_time",
            "route_data",
            "logs_data",
            "coordinates",
            "status",
            "progress",
            "error_message",
            "map_status",
            "map_progress",
            "map_error_message",
            "is_completed",
            "is_map_ready",
            "overall_progress",
            "map_url",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "total_distance",
            "total_driving_time",
            "total_trip_time",
            "route_data",
            "logs_data",
            "coordinates",
            "status",
            "progress",
            "error_message",
            "map_status",
            "map_progress",
            "map_error_message",
        ]

    def get_map_url(self, obj):
        """Safely get map URL."""
        if obj.map_file and obj.map_file.name:
            try:
                return obj.map_file.url
            except ValueError:
                return None
        return None


class TripInputSerializer(serializers.Serializer):
    """Serializer for trip calculation input."""

    current_location = serializers.CharField(max_length=255)
    pickup_location = serializers.CharField(max_length=255)
    dropoff_location = serializers.CharField(max_length=255)
    current_cycle_used = serializers.FloatField(
        min_value=0,
        max_value=70,
    )

    def validate_current_cycle_used(self, value: float) -> float:
        """Validate current cycle hours."""
        if value < 0 or value > 70:
            raise serializers.ValidationError(
                "Current cycle hours must be between 0 and 70"
            )
        return value

    def validate_current_location(self, value: str) -> str:
        """Validate current location is not empty."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Current location cannot be empty")
        return value

    def validate_pickup_location(self, value: str) -> str:
        """Validate pickup location is not empty."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Pickup location cannot be empty")
        return value

    def validate_dropoff_location(self, value: str) -> str:
        """Validate dropoff location is not empty."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Dropoff location cannot be empty")
        return value


class TripStatusSerializer(serializers.Serializer):
    """Serializer for trip status response."""

    id = serializers.IntegerField()
    status = serializers.CharField()
    progress = serializers.IntegerField()
    error_message = serializers.CharField(allow_null=True)
    map_status = serializers.CharField()
    map_progress = serializers.IntegerField()
    map_error_message = serializers.CharField(allow_null=True)
    overall_progress = serializers.IntegerField()
    is_completed = serializers.BooleanField()
    is_map_ready = serializers.BooleanField()
    total_distance = serializers.FloatField(allow_null=True)
    total_driving_time = serializers.FloatField(allow_null=True)
    map_url = serializers.CharField(allow_null=True)


class MapStatusSerializer(serializers.Serializer):
    """Serializer for map generation status."""

    trip_id = serializers.IntegerField()
    map_status = serializers.CharField()
    map_progress = serializers.IntegerField()
    map_error_message = serializers.CharField(allow_null=True)
    is_map_ready = serializers.BooleanField()
    map_url = serializers.CharField(allow_null=True)


class TripResultSerializer(serializers.Serializer):
    """Serializer for trip calculation result response."""

    id = serializers.IntegerField()
    status = serializers.CharField()
    message = serializers.CharField()
    total_distance = serializers.FloatField(required=False)
    total_driving_time = serializers.FloatField(required=False)
    total_trip_time = serializers.FloatField(required=False)
    route_data = serializers.JSONField(required=False)
    logs_data = serializers.JSONField(required=False)
    error_message = serializers.CharField(required=False)
