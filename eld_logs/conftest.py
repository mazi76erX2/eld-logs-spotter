import pytest
from django.core.files.base import ContentFile
from rest_framework.test import APIClient
from route_calculator.models import TripCalculation


@pytest.fixture
def api_client():
    """Return DRF API client."""
    return APIClient()


@pytest.fixture
def sample_trip_data():
    """Sample trip input data."""
    return {
        "current_location": "Los Angeles, CA",
        "pickup_location": "Phoenix, AZ",
        "dropoff_location": "Dallas, TX",
        "current_cycle_used": 20.0,
    }


@pytest.fixture
def sample_coordinates():
    """Sample coordinates."""
    return {
        "current": {"lat": 34.0522, "lon": -118.2437},
        "pickup": {"lat": 33.4484, "lon": -112.0740},
        "dropoff": {"lat": 32.7767, "lon": -96.7970},
    }


@pytest.fixture
def pending_trip(db):
    """Create a pending trip."""
    return TripCalculation.objects.create(
        current_location="Los Angeles, CA",
        pickup_location="Phoenix, AZ",
        dropoff_location="Dallas, TX",
        current_cycle_used=20.0,
        status=TripCalculation.JobStatus.PENDING,
        progress=0,
    )


@pytest.fixture
def processing_trip(db):
    """Create a processing trip."""
    return TripCalculation.objects.create(
        current_location="Los Angeles, CA",
        pickup_location="Phoenix, AZ",
        dropoff_location="Dallas, TX",
        current_cycle_used=20.0,
        status=TripCalculation.JobStatus.PROCESSING,
        progress=50,
    )


@pytest.fixture
def completed_trip(db):
    """Create a completed trip (without map)."""
    return TripCalculation.objects.create(
        current_location="Los Angeles, CA",
        pickup_location="Phoenix, AZ",
        dropoff_location="Dallas, TX",
        current_cycle_used=20.0,
        status=TripCalculation.JobStatus.COMPLETED,
        progress=100,
        total_distance=1000.0,
        total_driving_time=15.0,
        total_trip_time=24.0,
        map_status=TripCalculation.MapStatus.NOT_STARTED,
        map_progress=0,
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


@pytest.fixture
def completed_trip_with_map(db):
    """Create a completed trip with map ready."""
    trip = TripCalculation.objects.create(
        current_location="Los Angeles, CA",
        pickup_location="Phoenix, AZ",
        dropoff_location="Dallas, TX",
        current_cycle_used=20.0,
        status=TripCalculation.JobStatus.COMPLETED,
        progress=100,
        total_distance=1000.0,
        total_driving_time=15.0,
        total_trip_time=24.0,
        map_status=TripCalculation.MapStatus.COMPLETED,  # Changed from READY to COMPLETED
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
    # Save actual file content
    trip.map_file.save("test_map.png", ContentFile(b"fake_image_bytes"), save=True)
    return trip


@pytest.fixture
def failed_trip(db):
    """Create a failed trip."""
    return TripCalculation.objects.create(
        current_location="Los Angeles, CA",
        pickup_location="Phoenix, AZ",
        dropoff_location="Dallas, TX",
        current_cycle_used=20.0,
        status=TripCalculation.JobStatus.FAILED,
        error_message="Test error message",
    )


@pytest.fixture
def trip_with_generating_map(db):
    """Create a trip with map generating."""
    return TripCalculation.objects.create(
        current_location="Los Angeles, CA",
        pickup_location="Phoenix, AZ",
        dropoff_location="Dallas, TX",
        current_cycle_used=20.0,
        status=TripCalculation.JobStatus.COMPLETED,
        progress=100,
        map_status=TripCalculation.MapStatus.GENERATING,
        map_progress=50,
    )
