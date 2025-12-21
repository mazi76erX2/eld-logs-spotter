from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.core.files.base import ContentFile
from route_calculator.models import TripCalculation
from route_calculator.tasks import (_convert_to_fmcsa_logs,
                                    calculate_trip_task, generate_map_task,
                                    send_progress_update)


@pytest.mark.django_db
class TestSendProgressUpdate:
    """Tests for send_progress_update function."""

    @patch("route_calculator.tasks.get_channel_layer")
    def test_sends_update_successfully(self, mock_get_channel_layer):
        """Test that progress updates are sent via WebSocket."""
        mock_channel_layer = Mock()
        mock_get_channel_layer.return_value = mock_channel_layer

        send_progress_update(
            trip_id=1,
            data={
                "stage": "geocoding",
                "progress": 25,
                "message": "Test message",
            },
        )

        mock_channel_layer.group_send.assert_called_once()
        call_args = mock_channel_layer.group_send.call_args
        assert call_args[0][0] == "trip_1"
        assert call_args[0][1]["type"] == "progress_update"
        assert call_args[0][1]["data"]["trip_id"] == 1
        assert call_args[0][1]["data"]["stage"] == "geocoding"

    @patch("route_calculator.tasks.get_channel_layer")
    def test_handles_no_channel_layer(self, mock_get_channel_layer):
        """Test that function handles missing channel layer gracefully."""
        mock_get_channel_layer.return_value = None

        # Should not raise exception
        send_progress_update(trip_id=1, data={"progress": 50})

    @patch("route_calculator.tasks.get_channel_layer")
    def test_handles_exception(self, mock_get_channel_layer):
        """Test that function handles exceptions gracefully."""
        mock_channel_layer = Mock()
        mock_channel_layer.group_send.side_effect = Exception("Connection error")
        mock_get_channel_layer.return_value = mock_channel_layer

        # Should not raise exception
        send_progress_update(trip_id=1, data={"progress": 50})


@pytest.mark.django_db
class TestCalculateTripTask:
    """Tests for calculate_trip_task Celery task."""

    @patch("route_calculator.tasks.generate_map_task.delay")
    @patch("route_calculator.tasks.send_progress_update")
    @patch("route_calculator.tasks.RouteService")
    @patch("route_calculator.tasks.HOSCalculator")
    def test_successful_calculation(
        self,
        mock_hos_calculator,
        mock_route_service,
        mock_send_progress,
        mock_map_task,
        pending_trip,
        sample_coordinates,
    ):
        """Test successful trip calculation."""
        # Setup mocks
        mock_route_instance = Mock()
        mock_route_service.return_value = mock_route_instance
        mock_route_instance.geocode_location.side_effect = [
            sample_coordinates["current"],
            sample_coordinates["pickup"],
            sample_coordinates["dropoff"],
        ]
        mock_route_instance.get_route.return_value = {
            "features": [
                {
                    "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
                    "properties": {},
                }
            ]
        }
        mock_route_instance.get_route_legs.return_value = [
            {"distance": 500, "duration": 8},
            {"distance": 600, "duration": 10},
        ]

        mock_hos_instance = Mock()
        mock_hos_calculator.return_value = mock_hos_instance
        mock_hos_instance.calculate_trip_segments.return_value = (
            [
                {"type": "drive", "duration": 8, "distance": 500},
                {"type": "drive", "duration": 10, "distance": 600},
            ],
            [],
        )

        mock_map_task.return_value = Mock(id="test-task-id")

        # Execute task
        result = calculate_trip_task(pending_trip.id)

        # Verify
        assert result == pending_trip.id

        pending_trip.refresh_from_db()
        assert pending_trip.status == TripCalculation.JobStatus.COMPLETED
        assert pending_trip.progress == 100
        assert pending_trip.total_distance == 1100.0
        assert pending_trip.coordinates is not None
        assert pending_trip.route_data is not None
        assert pending_trip.logs_data is not None

        # Verify map task was triggered
        mock_map_task.assert_called_once_with(pending_trip.id)

    @patch("route_calculator.tasks.send_progress_update")
    @patch("route_calculator.tasks.RouteService")
    def test_geocoding_failure(
        self,
        mock_route_service,
        mock_send_progress,
        pending_trip,
    ):
        """Test handling of geocoding failure."""
        mock_route_instance = Mock()
        mock_route_service.return_value = mock_route_instance
        mock_route_instance.geocode_location.return_value = None

        with pytest.raises(Exception):
            calculate_trip_task(pending_trip.id)

        pending_trip.refresh_from_db()
        assert pending_trip.status == TripCalculation.JobStatus.FAILED
        assert "geocode" in pending_trip.error_message.lower()

    @patch("route_calculator.tasks.send_progress_update")
    def test_trip_not_found(self, mock_send_progress):
        """Test handling of non-existent trip."""
        result = calculate_trip_task(99999)
        assert result is None

    @patch("route_calculator.tasks.send_progress_update")
    @patch("route_calculator.tasks.RouteService")
    def test_route_calculation_failure(
        self,
        mock_route_service,
        mock_send_progress,
        pending_trip,
        sample_coordinates,
    ):
        """Test handling of route calculation failure."""
        mock_route_instance = Mock()
        mock_route_service.return_value = mock_route_instance
        mock_route_instance.geocode_location.side_effect = [
            sample_coordinates["current"],
            sample_coordinates["pickup"],
            sample_coordinates["dropoff"],
        ]
        mock_route_instance.get_route.return_value = None

        with pytest.raises(Exception):
            calculate_trip_task(pending_trip.id)

        pending_trip.refresh_from_db()
        assert pending_trip.status == TripCalculation.JobStatus.FAILED

    @patch("route_calculator.tasks.send_progress_update")
    def test_progress_updates_sent(self, mock_send_progress, pending_trip):
        """Test that progress updates are sent during calculation."""
        with patch("route_calculator.tasks.RouteService") as mock_route:
            mock_route_instance = Mock()
            mock_route.return_value = mock_route_instance
            mock_route_instance.geocode_location.return_value = None

            try:
                calculate_trip_task(pending_trip.id)
            except Exception:
                pass

        # Verify progress updates were called
        assert mock_send_progress.call_count > 0


@pytest.mark.django_db
class TestGenerateMapTask:
    """Tests for generate_map_task Celery task."""

    @patch("route_calculator.tasks.send_progress_update")
    @patch("route_calculator.tasks.MapGenerator")
    def test_successful_map_generation(
        self,
        mock_map_generator,
        mock_send_progress,
        completed_trip,
    ):
        """Test successful map generation."""
        # Reset map status for testing
        completed_trip.map_status = TripCalculation.MapStatus.NOT_STARTED
        completed_trip.map_progress = 0
        completed_trip.save()

        mock_generator_instance = Mock()
        mock_map_generator.return_value = mock_generator_instance
        mock_generator_instance.generate_route_map.return_value = b"fake_image_bytes"

        result = generate_map_task(completed_trip.id)

        completed_trip.refresh_from_db()
        assert completed_trip.map_status == TripCalculation.MapStatus.COMPLETED
        assert completed_trip.map_progress == 100
        assert result is not None

    @patch("route_calculator.tasks.send_progress_update")
    def test_incomplete_trip(self, mock_send_progress, processing_trip):
        """Test that map generation fails for incomplete trip."""
        result = generate_map_task(processing_trip.id)
        assert result is None

    @patch("route_calculator.tasks.send_progress_update")
    def test_trip_not_found(self, mock_send_progress):
        """Test handling of non-existent trip."""
        result = generate_map_task(99999)
        assert result is None

    @patch("route_calculator.tasks.send_progress_update")
    def test_missing_coordinates(self, mock_send_progress, completed_trip):
        """Test handling of missing coordinates."""
        completed_trip.coordinates = None
        completed_trip.map_status = TripCalculation.MapStatus.NOT_STARTED
        completed_trip.save()

        with pytest.raises(Exception):
            generate_map_task(completed_trip.id)

        completed_trip.refresh_from_db()
        assert completed_trip.map_status == TripCalculation.MapStatus.FAILED

    @patch("route_calculator.tasks.send_progress_update")
    @patch("route_calculator.tasks.MapGenerator")
    def test_map_generator_exception(
        self,
        mock_map_generator,
        mock_send_progress,
        completed_trip,
    ):
        """Test handling of map generator exception."""
        completed_trip.map_status = TripCalculation.MapStatus.NOT_STARTED
        completed_trip.save()

        mock_generator_instance = Mock()
        mock_map_generator.return_value = mock_generator_instance
        mock_generator_instance.generate_route_map.side_effect = Exception(
            "Tile fetch failed"
        )

        with pytest.raises(Exception):
            generate_map_task(completed_trip.id)

        completed_trip.refresh_from_db()
        assert completed_trip.map_status == TripCalculation.MapStatus.FAILED
        assert "Tile fetch failed" in completed_trip.map_error_message


@pytest.mark.django_db
class TestConvertToFMCSALogs:
    """Tests for _convert_to_fmcsa_logs function."""

    def test_single_day_trip(self):
        """Test conversion of single day trip."""
        segments = [
            {"type": "start", "duration": 0, "distance": 0, "location": "Start"},
            {"type": "drive", "duration": 5, "distance": 300, "location": "Highway"},
            {"type": "pickup", "duration": 1, "distance": 0, "location": "Pickup"},
            {"type": "drive", "duration": 4, "distance": 200, "location": "Highway"},
            {"type": "dropoff", "duration": 1, "distance": 0, "location": "Dropoff"},
        ]

        result = _convert_to_fmcsa_logs(
            trip_id=1,
            segments=segments,
            daily_logs_summary=[],
            current_location="Los Angeles, CA",
            pickup_location="Phoenix, AZ",
            dropoff_location="Dallas, TX",
            total_distance=500,
        )

        assert len(result) == 1
        assert result[0]["total_miles"] == 500
        assert len(result[0]["events"]) > 0
        assert result[0]["from_address"] == "Los Angeles, CA"
        assert result[0]["to_address"] == "Dallas, TX"

    def test_multi_day_trip(self):
        """Test conversion of multi-day trip."""
        segments = [
            {"type": "drive", "duration": 11, "distance": 600, "location": "Highway"},
            {"type": "rest", "duration": 10, "distance": 0, "location": "Rest Stop"},
            {"type": "drive", "duration": 11, "distance": 600, "location": "Highway"},
            {"type": "rest", "duration": 10, "distance": 0, "location": "Rest Stop"},
            {"type": "drive", "duration": 5, "distance": 300, "location": "Highway"},
        ]

        result = _convert_to_fmcsa_logs(
            trip_id=1,
            segments=segments,
            daily_logs_summary=[],
            current_location="Los Angeles, CA",
            pickup_location="Phoenix, AZ",
            dropoff_location="Dallas, TX",
            total_distance=1500,
        )

        # Should span multiple days
        assert len(result) >= 2

    def test_status_mapping(self):
        """Test correct status mapping for different segment types."""
        segments = [
            {"type": "drive", "duration": 4, "distance": 200, "location": "Highway"},
            {"type": "pickup", "duration": 1, "distance": 0, "location": "Pickup"},
            {"type": "rest", "duration": 2, "distance": 0, "location": "Rest"},
            {"type": "break", "duration": 0.5, "distance": 0, "location": "Break"},
            {"type": "fuel", "duration": 0.5, "distance": 0, "location": "Fuel"},
        ]

        result = _convert_to_fmcsa_logs(
            trip_id=1,
            segments=segments,
            daily_logs_summary=[],
            current_location="Start",
            pickup_location="Pickup",
            dropoff_location="End",
            total_distance=200,
        )

        events = result[0]["events"]
        statuses = [e["status"] for e in events]

        assert "driving" in statuses
        assert "onDuty" in statuses
        assert "sleeper" in statuses
        assert "offDuty" in statuses

    def test_empty_segments(self):
        """Test handling of empty segments."""
        result = _convert_to_fmcsa_logs(
            trip_id=1,
            segments=[],
            daily_logs_summary=[],
            current_location="Start",
            pickup_location="Pickup",
            dropoff_location="End",
            total_distance=0,
        )

        assert result == []
