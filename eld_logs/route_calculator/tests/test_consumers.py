from unittest.mock import AsyncMock, Mock

import pytest
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.urls import path
from route_calculator.consumers import TripListConsumer, TripProgressConsumer
from route_calculator.models import TripCalculation


# Create test application
def get_test_application():
    """Create test ASGI application with WebSocket routes."""
    return URLRouter(
        [
            path("ws/trips/<int:trip_id>/progress/", TripProgressConsumer.as_asgi()),
            path("ws/trips/", TripListConsumer.as_asgi()),
        ]
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestTripProgressConsumer:
    """Tests for TripProgressConsumer WebSocket consumer."""

    async def test_connect_with_valid_trip(self, pending_trip):
        """Test successful WebSocket connection with valid trip."""
        application = get_test_application()
        communicator = WebsocketCommunicator(
            application, f"/ws/trips/{pending_trip.id}/progress/"
        )

        connected, _ = await communicator.connect()
        assert connected is True

        # Should receive initial status message
        response = await communicator.receive_json_from()
        assert response["type"] == "status"
        assert response["trip_id"] == pending_trip.id

        await communicator.disconnect()

    async def test_connect_with_invalid_trip(self):
        """Test WebSocket connection with non-existent trip."""
        application = get_test_application()
        communicator = WebsocketCommunicator(application, "/ws/trips/99999/progress/")

        connected, close_code = await communicator.connect()
        # Should close connection with error code
        assert connected is False or close_code == 4004

    async def test_ping_pong(self, pending_trip):
        """Test ping/pong keep-alive mechanism."""
        application = get_test_application()
        communicator = WebsocketCommunicator(
            application, f"/ws/trips/{pending_trip.id}/progress/"
        )

        await communicator.connect()
        # Consume initial status message
        await communicator.receive_json_from()

        # Send ping
        await communicator.send_json_to({"type": "ping"})

        # Should receive pong
        response = await communicator.receive_json_from()
        assert response["type"] == "pong"
        assert response["trip_id"] == pending_trip.id
        assert "timestamp" in response

        await communicator.disconnect()

    async def test_get_status_request(self, completed_trip):
        """Test requesting current status."""
        application = get_test_application()
        communicator = WebsocketCommunicator(
            application, f"/ws/trips/{completed_trip.id}/progress/"
        )

        await communicator.connect()
        # Consume initial status message
        await communicator.receive_json_from()

        # Request status
        await communicator.send_json_to({"type": "get_status"})

        # Should receive status response
        response = await communicator.receive_json_from()
        assert response["type"] == "status"
        assert response["trip_id"] == completed_trip.id
        assert response["status"] == "completed"
        assert response["progress"] == 100

        await communicator.disconnect()

    async def test_invalid_json(self, pending_trip):
        """Test handling of invalid JSON."""
        application = get_test_application()
        communicator = WebsocketCommunicator(
            application, f"/ws/trips/{pending_trip.id}/progress/"
        )

        await communicator.connect()
        # Consume initial status message
        await communicator.receive_json_from()

        # Send invalid JSON
        await communicator.send_to(text_data="not valid json")

        # Should receive error response
        response = await communicator.receive_json_from()
        assert response["type"] == "error"
        assert "Invalid JSON" in response["message"]

        await communicator.disconnect()

    async def test_unknown_message_type(self, pending_trip):
        """Test handling of unknown message type."""
        import asyncio

        application = get_test_application()
        communicator = WebsocketCommunicator(
            application, f"/ws/trips/{pending_trip.id}/progress/"
        )

        connected, _ = await communicator.connect()
        assert connected is True

        # Consume initial status message
        await communicator.receive_json_from()

        # Send unknown message type
        await communicator.send_json_to({"type": "unknown_type"})

        # Should not crash - just ignore unknown types
        # Try to receive with timeout - should timeout without error
        try:
            await asyncio.wait_for(communicator.receive_json_from(), timeout=0.5)
        except asyncio.TimeoutError:
            pass  # Timeout is expected - no response for unknown types
        try:
            await asyncio.wait_for(communicator.disconnect(), timeout=1.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass  # Ignore cleanup errors

    async def test_progress_update_handler(self, pending_trip):
        """Test handling of progress updates from Celery."""
        # Test the handler directly without WebSocket connection
        consumer = TripProgressConsumer()
        consumer.trip_id = pending_trip.id

        # Create mock for send method
        sent_messages = []

        async def mock_send_json(data):
            sent_messages.append(data)

        consumer.send_json = mock_send_json
        consumer.get_trip = AsyncMock(return_value=pending_trip)

        await consumer.progress_update(
            {
                "data": {
                    "stage": "geocoding",
                    "progress": 25,
                    "message": "Geocoding locations...",
                }
            }
        )

        assert len(sent_messages) == 1
        assert sent_messages[0]["type"] == "progress"
        assert sent_messages[0]["progress"] == 25

    async def test_status_includes_map_url(self, completed_trip):
        """Test that status includes map info when available."""
        application = get_test_application()
        communicator = WebsocketCommunicator(
            application, f"/ws/trips/{completed_trip.id}/progress/"
        )

        await communicator.connect()
        response = await communicator.receive_json_from()

        assert response["type"] == "status"
        # Note: is_map_ready may be False if no actual file
        assert "is_map_ready" in response

        await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestTripListConsumer:
    """Tests for TripListConsumer WebSocket consumer."""

    async def test_connect(self):
        """Test successful connection to trips list WebSocket."""
        application = get_test_application()
        communicator = WebsocketCommunicator(application, "/ws/trips/")

        connected, _ = await communicator.connect()
        assert connected is True

        await communicator.disconnect()

    async def test_ping_pong(self):
        """Test ping/pong mechanism."""
        application = get_test_application()
        communicator = WebsocketCommunicator(application, "/ws/trips/")

        await communicator.connect()

        await communicator.send_json_to({"type": "ping"})

        response = await communicator.receive_json_from()
        assert response["type"] == "pong"
        assert "timestamp" in response

        await communicator.disconnect()

    async def test_trip_created_handler(self):
        """Test handling of trip created event."""
        consumer = TripListConsumer()

        sent_messages = []

        async def mock_send_json(data):
            sent_messages.append(data)

        consumer.send_json = mock_send_json

        await consumer.trip_created({"trip_id": 123})

        assert len(sent_messages) == 1
        assert sent_messages[0]["type"] == "trip_created"
        assert sent_messages[0]["trip_id"] == 123

    async def test_trip_updated_handler(self):
        """Test handling of trip updated event."""
        consumer = TripListConsumer()

        sent_messages = []

        async def mock_send_json(data):
            sent_messages.append(data)

        consumer.send_json = mock_send_json

        await consumer.trip_updated(
            {
                "trip_id": 123,
                "status": "completed",
            }
        )

        assert len(sent_messages) == 1
        assert sent_messages[0]["type"] == "trip_updated"
        assert sent_messages[0]["trip_id"] == 123
        assert sent_messages[0]["status"] == "completed"
