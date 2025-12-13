from rest_framework import serializers

from .models import TripCalculation


class TripCalculationSerializer(serializers.ModelSerializer):
    """Serializer for TripCalculation model."""

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
            "error_message",
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
            "error_message",
        ]


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
