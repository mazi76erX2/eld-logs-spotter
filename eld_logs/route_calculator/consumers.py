import json
import logging
from typing import Any, Optional

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

logger = logging.getLogger(__name__)


class TripProgressConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for trip calculation progress updates.

    Handles:
    - Connection/disconnection for specific trip IDs
    - Real-time progress updates from Celery tasks
    - Client requests for current status
    - Ping/pong for connection keep-alive
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.trip_id: Optional[int] = None
        self.group_name: Optional[str] = None

    async def connect(self) -> None:
        """
        Handle WebSocket connection.

        Extracts trip_id from URL and joins the corresponding group.
        """
        try:
            self.trip_id = int(self.scope["url_route"]["kwargs"]["trip_id"])
            self.group_name = f"trip_{self.trip_id}"

            # Verify trip exists
            trip = await self.get_trip()
            if not trip:
                logger.warning(
                    "WebSocket connection rejected - Trip %s not found",
                    self.trip_id,
                )
                await self.close(code=4004)
                return

            # Join trip-specific group
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

            logger.info(
                "WebSocket connected for trip %s (channel: %s)",
                self.trip_id,
                self.channel_name,
            )

            # Send initial status
            await self.send_current_status()

        except (ValueError, KeyError) as e:
            logger.error("Invalid trip_id in WebSocket URL: %s", e)
            await self.close(code=4000)

    async def disconnect(self, close_code: int) -> None:
        """
        Handle WebSocket disconnection.

        Removes channel from the trip group.
        """
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info(
                "WebSocket disconnected for trip %s (code: %s)",
                self.trip_id,
                close_code,
            )

    async def receive(self, text_data: str) -> None:
        """
        Handle incoming WebSocket messages from client.

        Supported message types:
        - ping: Keep-alive ping
        - get_status: Request current trip status
        """
        try:
            data = json.loads(text_data)
            message_type = data.get("type", "")

            if message_type == "ping":
                await self.send_json(
                    {
                        "type": "pong",
                        "trip_id": self.trip_id,
                        "timestamp": timezone.now().isoformat(),
                    }
                )

            elif message_type == "get_status":
                await self.send_current_status()

            else:
                logger.debug(
                    "Unknown message type received for trip %s: %s",
                    self.trip_id,
                    message_type,
                )

        except json.JSONDecodeError as e:
            logger.warning(
                "Invalid JSON received for trip %s: %s",
                self.trip_id,
                e,
            )
            await self.send_json(
                {
                    "type": "error",
                    "message": "Invalid JSON format",
                }
            )

    async def progress_update(self, event: dict[str, Any]) -> None:
        """
        Handle progress update from Celery task (via channel layer).

        This method is called when a Celery task sends a progress update
        using channel_layer.group_send with type "progress_update".
        """
        data = event.get("data", {})

        # Build the response message
        message = {
            "type": "progress",
            "trip_id": self.trip_id,
            "timestamp": data.get("timestamp", timezone.now().isoformat()),
            "stage": data.get("stage"),
            "status": data.get("status"),
            "progress": data.get("progress"),
            "message": data.get("message"),
            "map_status": data.get("map_status"),
            "map_progress": data.get("map_progress"),
            "map_url": data.get("map_url"),
            "total_distance": data.get("total_distance"),
            "total_driving_time": data.get("total_driving_time"),
            "num_days": data.get("num_days"),
            "error": data.get("error"),
        }

        # Remove None values for cleaner response
        message = {k: v for k, v in message.items() if v is not None}

        # Add computed fields
        trip = await self.get_trip()
        if trip:
            message["overall_progress"] = trip.overall_progress
            message["is_completed"] = trip.is_completed
            message["is_map_ready"] = trip.is_map_ready

        await self.send_json(message)

    async def send_current_status(self) -> None:
        """
        Send current trip status to the client.
        """
        trip = await self.get_trip()

        if not trip:
            await self.send_json(
                {
                    "type": "error",
                    "trip_id": self.trip_id,
                    "message": "Trip not found",
                }
            )
            return

        message = {
            "type": "status",
            "trip_id": self.trip_id,
            "timestamp": timezone.now().isoformat(),
            "status": trip.status,
            "progress": trip.progress,
            "map_status": trip.map_status,
            "map_progress": trip.map_progress,
            "overall_progress": trip.overall_progress,
            "is_completed": trip.is_completed,
            "is_map_ready": trip.is_map_ready,
            "total_distance": trip.total_distance,
            "total_driving_time": trip.total_driving_time,
            "total_trip_time": trip.total_trip_time,
            "error_message": trip.error_message,
            "map_error_message": trip.map_error_message,
        }

        # Add map URL if available
        if trip.is_map_ready and trip.map_file:
            message["map_url"] = trip.map_file.url

        # Remove None values
        message = {k: v for k, v in message.items() if v is not None}

        await self.send_json(message)

    async def send_json(self, data: dict[str, Any]) -> None:
        """
        Send JSON data to the WebSocket client.
        """
        await self.send(text_data=json.dumps(data))

    @database_sync_to_async
    def get_trip(self) -> Optional[Any]:
        """
        Fetch trip from database asynchronously.

        Returns:
            TripCalculation instance or None if not found.
        """
        from .models import TripCalculation

        try:
            return TripCalculation.objects.get(id=self.trip_id)
        except TripCalculation.DoesNotExist:
            return None


class TripListConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time updates on the trips list.

    Useful for dashboard updates when new trips are created or
    status changes occur.
    """

    GROUP_NAME = "trips_list"

    async def connect(self) -> None:
        """Handle WebSocket connection."""
        await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)
        await self.accept()
        logger.info(
            "WebSocket connected to trips list (channel: %s)", self.channel_name
        )

    async def disconnect(self, close_code: int) -> None:
        """Handle WebSocket disconnection."""
        await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)
        logger.info("WebSocket disconnected from trips list (code: %s)", close_code)

    async def receive(self, text_data: str) -> None:
        """Handle incoming messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get("type", "")

            if message_type == "ping":
                await self.send_json(
                    {
                        "type": "pong",
                        "timestamp": timezone.now().isoformat(),
                    }
                )

        except json.JSONDecodeError:
            pass

    async def trip_created(self, event: dict[str, Any]) -> None:
        """Handle new trip creation notification."""
        await self.send_json(
            {
                "type": "trip_created",
                "trip_id": event.get("trip_id"),
                "timestamp": timezone.now().isoformat(),
            }
        )

    async def trip_updated(self, event: dict[str, Any]) -> None:
        """Handle trip update notification."""
        await self.send_json(
            {
                "type": "trip_updated",
                "trip_id": event.get("trip_id"),
                "status": event.get("status"),
                "timestamp": timezone.now().isoformat(),
            }
        )

    async def send_json(self, data: dict[str, Any]) -> None:
        """Send JSON data to the WebSocket client."""
        await self.send(text_data=json.dumps(data))


# In route_calculator/consumers.py - add this simple test consumer
class TestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info("Test WebSocket connecting...")
        await self.accept()
        await self.send(text_data=json.dumps({"message": "Connected!"}))
        logger.info("Test WebSocket connected!")

    async def disconnect(self, close_code):
        logger.info(f"Test WebSocket disconnected: {close_code}")

    async def receive(self, text_data):
        await self.send(text_data=json.dumps({"echo": text_data}))
