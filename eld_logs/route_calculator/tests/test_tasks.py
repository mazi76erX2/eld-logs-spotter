from unittest.mock import MagicMock, patch

import pytest

from ..models import TripCalculation
from ..tasks import calculate_trip_task


@pytest.fixture
def trip(db):
    """Create a pending trip calculation."""
    return TripCalculation.objects.create(
        current_location="Dallas, TX",
        pickup_location="Houston, TX",
        dropoff_location="Atlanta, GA",
        current_cycle_used=10,
        status=TripCalculation.JobStatus.PENDING,
    )


# -------------------------------------------------
# SUCCESS CASE
# -------------------------------------------------
@pytest.mark.django_db
@patch("route_calculator.tasks.RouteService")
@patch("route_calculator.tasks.HOSCalculator")
def test_calculate_trip_task_success(
    mock_hos_cls,
    mock_route_cls,
    trip,
):
    """Task completes successfully and saves results."""

    # ---- Mock RouteService ----
    mock_route = MagicMock()
    mock_route.geocode_location.side_effect = [
        {"lat": 32.7, "lon": -96.8, "name": "Dallas, TX"},
        {"lat": 29.7, "lon": -95.3, "name": "Houston, TX"},
        {"lat": 33.7, "lon": -84.3, "name": "Atlanta, GA"},
    ]
    mock_route.get_route.return_value = {
        "features": [{"geometry": {"type": "LineString", "coordinates": []}}]
    }
    mock_route.get_route_legs.return_value = [{"distance": 800.0, "duration": 15.0}]
    mock_route_cls.return_value = mock_route

    # ---- Mock HOSCalculator ----
    mock_hos = MagicMock()
    mock_hos.calculate_trip_segments.return_value = (
        [
            {"type": "drive", "duration": 10.0, "distance": 550},
            {"type": "rest", "duration": 10.0, "distance": 0.0},
        ],
        [{"day": 1}],
    )
    mock_hos_cls.return_value = mock_hos

    # ---- Execute task ----
    result = calculate_trip_task(trip.id)

    # ---- Assertions ----
    trip.refresh_from_db()

    assert result == trip.id
    assert trip.status == TripCalculation.JobStatus.COMPLETED
    assert trip.total_distance == 800.0
    assert trip.total_driving_time == 10.0
    assert trip.route_data is not None
    assert trip.logs_data is not None


# -------------------------------------------------
# TRIP NOT FOUND
# -------------------------------------------------
@pytest.mark.django_db
def test_calculate_trip_task_trip_not_found():
    """Returns None if trip does not exist."""
    result = calculate_trip_task(999999)
    assert result is None


# -------------------------------------------------
# GEOCODING FAILURE
# -------------------------------------------------
@pytest.mark.django_db
@patch("route_calculator.tasks.RouteService")
def test_calculate_trip_task_geocode_failure(
    mock_route_cls,
    trip,
):
    """Task fails if geocoding fails."""
    mock_route = MagicMock()
    mock_route.geocode_location.return_value = None
    mock_route_cls.return_value = mock_route

    with pytest.raises(Exception):
        calculate_trip_task(trip.id)

    trip.refresh_from_db()
    assert trip.status == TripCalculation.JobStatus.FAILED
    assert trip.error_message


# -------------------------------------------------
# RETRY BEHAVIOR
# -------------------------------------------------
@pytest.mark.django_db
@patch("route_calculator.tasks.calculate_trip_task.retry")
@patch("route_calculator.tasks.RouteService")
def test_calculate_trip_task_retry_on_exception(
    mock_route_cls,
    mock_retry,
    trip,
):
    """Celery retry is triggered on exception."""
    mock_route = MagicMock()
    mock_route.geocode_location.side_effect = Exception("Boom")
    mock_route_cls.return_value = mock_route

    with pytest.raises(Exception):
        calculate_trip_task(trip.id)

    assert mock_retry.called
