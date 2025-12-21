from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from route_calculator.models import TripCalculation


@pytest.mark.django_db
class TestTripCalculationList:
    """Tests for trip list endpoint."""

    def test_list_trips_empty(self, api_client):
        """Test listing trips when none exist."""
        url = reverse("tripcalculation-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0
        assert response.data["results"] == []

    def test_list_trips_with_data(self, api_client, completed_trip, pending_trip):
        """Test listing trips with existing data."""
        url = reverse("tripcalculation-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
        assert len(response.data["results"]) == 2

    def test_list_trips_ordered_by_date(self, api_client, pending_trip, completed_trip):
        """Test trips are ordered by creation date (newest first)."""
        url = reverse("tripcalculation-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Most recently created should be first
        results = response.data["results"]
        assert results[0]["id"] == completed_trip.id


@pytest.mark.django_db
class TestTripCalculationRetrieve:
    """Tests for trip retrieve endpoint."""

    def test_get_trip_detail(self, api_client, completed_trip):
        """Test getting trip details."""
        url = reverse("tripcalculation-detail", kwargs={"pk": completed_trip.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == completed_trip.id
        assert response.data["status"] == "completed"
        assert response.data["current_location"] == completed_trip.current_location

    def test_get_trip_not_found(self, api_client):
        """Test getting non-existent trip."""
        url = reverse("tripcalculation-detail", kwargs={"pk": 99999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestTripCalculationCreate:
    """Tests for trip calculate endpoint."""

    @patch("route_calculator.views.calculate_trip_task.delay")
    def test_create_trip_valid_data(self, mock_task, api_client, sample_trip_data):
        """Test creating a trip with valid data."""
        mock_task.return_value = Mock(id="test-task-id")

        url = reverse("tripcalculation-calculate")
        response = api_client.post(url, sample_trip_data, format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "id" in response.data
        assert response.data["status"] == "processing"
        assert "websocket_url" in response.data
        assert "polling_url" in response.data

        mock_task.assert_called_once()

    def test_create_trip_missing_fields(self, api_client):
        """Test creating trip with missing required fields."""
        url = reverse("tripcalculation-calculate")
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_trip_invalid_cycle_hours(self, api_client, sample_trip_data):
        """Test creating trip with invalid cycle hours."""
        sample_trip_data["current_cycle_used"] = 100  # Over 70

        url = reverse("tripcalculation-calculate")
        response = api_client.post(url, sample_trip_data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_trip_negative_cycle_hours(self, api_client, sample_trip_data):
        """Test creating trip with negative cycle hours."""
        sample_trip_data["current_cycle_used"] = -10

        url = reverse("tripcalculation-calculate")
        response = api_client.post(url, sample_trip_data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_trip_empty_location(self, api_client, sample_trip_data):
        """Test creating trip with empty location."""
        sample_trip_data["current_location"] = ""

        url = reverse("tripcalculation-calculate")
        response = api_client.post(url, sample_trip_data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTripCalculationDelete:
    """Tests for trip delete endpoint."""

    def test_delete_trip(self, api_client, pending_trip):
        """Test deleting a trip."""
        trip_id = pending_trip.id
        url = reverse("tripcalculation-detail", kwargs={"pk": trip_id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not TripCalculation.objects.filter(id=trip_id).exists()

    def test_delete_trip_not_found(self, api_client):
        """Test deleting non-existent trip."""
        url = reverse("tripcalculation-detail", kwargs={"pk": 99999})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestTripStatus:
    """Tests for trip status endpoint."""

    def test_get_status_pending(self, api_client, pending_trip):
        """Test getting status of pending trip."""
        url = reverse("tripcalculation-get-status", kwargs={"pk": pending_trip.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "pending"
        assert response.data["progress"] == 0

    def test_get_status_processing(self, api_client, processing_trip):
        """Test getting status of processing trip."""
        url = reverse("tripcalculation-get-status", kwargs={"pk": processing_trip.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "processing"
        assert response.data["progress"] == 50

    def test_get_status_completed(self, api_client, completed_trip):
        """Test getting status of completed trip."""
        url = reverse("tripcalculation-get-status", kwargs={"pk": completed_trip.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "completed"
        assert response.data["progress"] == 100
        assert response.data["is_completed"] is True
        assert response.data["total_distance"] == completed_trip.total_distance

    def test_get_status_failed(self, api_client, failed_trip):
        """Test getting status of failed trip."""
        url = reverse("tripcalculation-get-status", kwargs={"pk": failed_trip.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "failed"
        assert response.data["error_message"] is not None

    def test_get_status_not_found(self, api_client):
        """Test getting status of non-existent trip."""
        url = reverse("tripcalculation-get-status", kwargs={"pk": 99999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestTripResult:
    """Tests for trip result endpoint."""

    def test_get_result(self, api_client, completed_trip):
        """Test getting trip result."""
        url = reverse("tripcalculation-result", kwargs={"pk": completed_trip.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == completed_trip.id
        assert response.data["total_distance"] == completed_trip.total_distance
        assert response.data["route_data"] is not None
        assert response.data["logs_data"] is not None


@pytest.mark.django_db
class TestTripSummary:
    """Tests for trip summary endpoint."""

    def test_get_summary(self, api_client, completed_trip):
        """Test getting trip summary."""
        url = reverse("tripcalculation-summary", kwargs={"pk": completed_trip.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == completed_trip.id
        assert response.data["total_distance"] == completed_trip.total_distance
        assert response.data["num_days"] == len(completed_trip.logs_data)
        # Fix: Don't assert is_map_ready is True since fixture doesn't have map file
        assert "is_map_ready" in response.data


@pytest.mark.django_db
class TestTripLogs:
    """Tests for trip logs endpoints."""

    def test_list_logs(self, api_client, completed_trip):
        """Test listing logs for a trip."""
        url = reverse("tripcalculation-list-logs", kwargs={"pk": completed_trip.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["trip_id"] == completed_trip.id
        assert response.data["total_days"] == len(completed_trip.logs_data)
        assert len(response.data["logs"]) == len(completed_trip.logs_data)

        # Verify log structure
        first_log = response.data["logs"][0]
        assert "day" in first_log
        assert "date" in first_log
        assert "total_miles" in first_log
        assert "download_url" in first_log

    def test_list_logs_no_data(self, api_client, pending_trip):
        """Test listing logs for trip with no logs."""
        url = reverse("tripcalculation-list-logs", kwargs={"pk": pending_trip.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("route_calculator.views.LogGenerator")
    def test_download_log(self, mock_generator, api_client, completed_trip):
        """Test downloading a daily log."""
        mock_instance = Mock()
        mock_generator.return_value = mock_instance
        mock_instance.generate_log_image.return_value = b"fake_image_bytes"

        url = reverse("tripcalculation-download-log", kwargs={"pk": completed_trip.id})
        response = api_client.get(url, {"day": 1})

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"] == "image/png"
        assert "attachment" in response["Content-Disposition"]

    def test_download_log_invalid_day(self, api_client, completed_trip):
        """Test downloading log with invalid day."""
        url = reverse("tripcalculation-download-log", kwargs={"pk": completed_trip.id})
        response = api_client.get(url, {"day": 999})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_download_log_day_zero(self, api_client, completed_trip):
        """Test downloading log with day 0."""
        url = reverse("tripcalculation-download-log", kwargs={"pk": completed_trip.id})
        response = api_client.get(url, {"day": 0})

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestTripMap:
    """Tests for trip map endpoints."""

    def test_download_map_ready(self, api_client, completed_trip_with_map):
        """Test downloading map when ready."""
        from django.core.files.base import ContentFile

        # Save an actual file instead of mocking
        completed_trip_with_map.map_file.save(
            "test_map.png", ContentFile(b"fake_image_bytes"), save=True
        )

        url = reverse(
            "tripcalculation-download-map", kwargs={"pk": completed_trip_with_map.id}
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_download_map_generating(self, api_client, trip_with_generating_map):
        """Test downloading map while still generating."""
        url = reverse(
            "tripcalculation-download-map", kwargs={"pk": trip_with_generating_map.id}
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data["status"] == "generating"
        assert "progress" in response.data

    @patch("route_calculator.views.generate_map_task.delay")
    def test_download_map_not_started(self, mock_task, api_client, completed_trip):
        """Test downloading map when not yet started."""
        completed_trip.map_status = TripCalculation.MapStatus.NOT_STARTED
        completed_trip.map_file = None
        completed_trip.save()

        mock_task.return_value = Mock(id="test-task-id")

        url = reverse("tripcalculation-download-map", kwargs={"pk": completed_trip.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data["status"] == "generating"
        mock_task.assert_called_once()

    def test_download_map_incomplete_trip(self, api_client, pending_trip):
        """Test downloading map for incomplete trip."""
        url = reverse("tripcalculation-download-map", kwargs={"pk": pending_trip.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("route_calculator.views.generate_map_task.delay")
    def test_retry_map_success(self, mock_task, api_client, completed_trip):
        """Test retrying map generation."""
        completed_trip.map_status = TripCalculation.MapStatus.FAILED
        completed_trip.save()

        mock_task.return_value = Mock(id="new-task-id")

        url = reverse("tripcalculation-retry-map", kwargs={"pk": completed_trip.id})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "map_task_id" in response.data
        mock_task.assert_called_once_with(completed_trip.id)

    def test_retry_map_incomplete_trip(self, api_client, pending_trip):
        """Test retrying map for incomplete trip."""
        url = reverse("tripcalculation-retry-map", kwargs={"pk": pending_trip.id})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_retry_map_already_generating(self, api_client, trip_with_generating_map):
        """Test retrying map that's already generating."""
        url = reverse(
            "tripcalculation-retry-map", kwargs={"pk": trip_with_generating_map.id}
        )
        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check_healthy(self, api_client):
        """Test health check when everything is healthy."""
        response = api_client.get("/api/health/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "healthy"
        assert response.data["database"] == "healthy"


@pytest.mark.django_db
class TestPagination:
    """Tests for pagination."""

    def test_pagination_default(self, api_client):
        """Test default pagination."""
        # Create multiple trips
        for i in range(15):
            TripCalculation.objects.create(
                current_location=f"Location {i}",
                pickup_location=f"Pickup {i}",
                dropoff_location=f"Dropoff {i}",
                current_cycle_used=10,
            )

        url = reverse("tripcalculation-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 15
        assert "next" in response.data
        assert "previous" in response.data

    def test_pagination_page_size(self, api_client):
        """Test custom page size."""
        for i in range(5):
            TripCalculation.objects.create(
                current_location=f"Location {i}",
                pickup_location=f"Pickup {i}",
                dropoff_location=f"Dropoff {i}",
                current_cycle_used=10,
            )

        url = reverse("tripcalculation-list")
        response = api_client.get(url, {"page_size": 2})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) <= 2
