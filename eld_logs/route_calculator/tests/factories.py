import factory
from factory.django import DjangoModelFactory
from route_calculator.models import TripCalculation


class TripCalculationFactory(DjangoModelFactory):
    """Factory for creating TripCalculation instances."""

    class Meta:
        model = TripCalculation

    current_location = factory.Faker("city", locale="en_US")
    pickup_location = factory.Faker("city", locale="en_US")
    dropoff_location = factory.Faker("city", locale="en_US")
    current_cycle_used = factory.Faker("pyfloat", min_value=0, max_value=70)
    status = TripCalculation.JobStatus.PENDING
    progress = 0

    class Params:
        completed = factory.Trait(
            status=TripCalculation.JobStatus.COMPLETED,
            progress=100,
            total_distance=1000.0,
            total_driving_time=15.0,
            total_trip_time=24.0,
            map_status=TripCalculation.MapStatus.COMPLETED,
            map_progress=100,
            coordinates={
                "current": {"lat": 34.0522, "lon": -118.2437},
                "pickup": {"lat": 33.4484, "lon": -112.0740},
                "dropoff": {"lat": 32.7767, "lon": -96.7970},
            },
            route_data={
                "segments": [],
                "geometry": {"type": "LineString", "coordinates": []},
            },
            logs_data=[
                {
                    "date": "01/15/2024",
                    "events": [{"start": 0, "end": 8, "status": "driving"}],
                    "total_miles": 500,
                    "remarks": [],
                }
            ],
        )

        failed = factory.Trait(
            status=TripCalculation.JobStatus.FAILED,
            error_message="Test error message",
        )

        processing = factory.Trait(
            status=TripCalculation.JobStatus.PROCESSING,
            progress=50,
        )
