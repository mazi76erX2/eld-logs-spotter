import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.core.files.base import ContentFile

from .models import TripCalculation
from .services.hos_calculator import HOSCalculator
from .services.map_generator import MapGenerator
from .services.route_service import RouteService

logger = logging.getLogger(__name__)


async def _async_group_send(channel_layer: Any, group: str, message: dict) -> None:
    """Async helper to send message to channel group."""
    await channel_layer.group_send(group, message)


def send_progress_update(trip_id: int, data: dict[str, Any]) -> None:
    """
    Send progress update via WebSocket to frontend.

    Args:
        trip_id: Trip ID to send update for
        data: Progress data to send
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(_async_group_send)(
                channel_layer,
                f"trip_{trip_id}",
                {
                    "type": "progress_update",
                    "data": {
                        "trip_id": trip_id,
                        "timestamp": datetime.now().isoformat(),
                        **data,
                    },
                },
            )
    except Exception as e:
        logger.warning(f"Failed to send WebSocket update for trip {trip_id}: {e}")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def calculate_trip_task(self, trip_id: int) -> Optional[int]:
    """
    Async task to calculate trip route and generate FMCSA-compliant logs.
    Sends progress updates via WebSocket.

    Args:
        trip_id: ID of TripCalculation instance

    Returns:
        Trip ID if successful, None otherwise
    """
    try:
        trip = TripCalculation.objects.get(id=trip_id)
        trip.status = TripCalculation.JobStatus.PROCESSING
        trip.progress = 5
        trip.save(update_fields=["status", "progress", "updated_at"])

        send_progress_update(
            trip_id,
            {
                "stage": "trip_calculation",
                "status": "processing",
                "progress": 5,
                "message": "Starting trip calculation...",
            },
        )

        logger.info("Starting calculation for trip %s", trip_id)

        # Initialize services
        route_service = RouteService()

        # =====================================================================
        # STAGE 1: Geocoding (5% -> 25%)
        # =====================================================================
        send_progress_update(
            trip_id,
            {
                "stage": "geocoding",
                "status": "processing",
                "progress": 10,
                "message": "Geocoding locations...",
            },
        )

        current_coord = route_service.geocode_location(trip.current_location)
        trip.update_progress(15)
        send_progress_update(
            trip_id, {"progress": 15, "message": "Geocoded current location"}
        )

        pickup_coord = route_service.geocode_location(trip.pickup_location)
        trip.update_progress(20)
        send_progress_update(
            trip_id, {"progress": 20, "message": "Geocoded pickup location"}
        )

        dropoff_coord = route_service.geocode_location(trip.dropoff_location)
        trip.update_progress(25)
        send_progress_update(
            trip_id, {"progress": 25, "message": "Geocoded dropoff location"}
        )

        if not all([current_coord, pickup_coord, dropoff_coord]):
            raise ValueError("Could not geocode one or more locations")

        # Store coordinates
        trip.coordinates = {
            "current": current_coord,
            "pickup": pickup_coord,
            "dropoff": dropoff_coord,
        }
        trip.save(update_fields=["coordinates", "updated_at"])

        # =====================================================================
        # STAGE 2: Route Calculation (25% -> 50%)
        # =====================================================================
        send_progress_update(
            trip_id,
            {
                "stage": "routing",
                "status": "processing",
                "progress": 30,
                "message": "Calculating optimal route...",
            },
        )

        coordinates = [
            [current_coord["lon"], current_coord["lat"]],
            [pickup_coord["lon"], pickup_coord["lat"]],
            [dropoff_coord["lon"], dropoff_coord["lat"]],
        ]

        route = route_service.get_route(coordinates)
        trip.update_progress(40)

        if not route:
            raise ValueError("Could not calculate route")

        route_legs = route_service.get_route_legs(route)
        trip.update_progress(50)

        if not route_legs:
            raise ValueError("No route legs found")

        send_progress_update(
            trip_id,
            {
                "stage": "routing",
                "progress": 50,
                "message": "Route calculated successfully",
            },
        )

        # Calculate totals
        total_distance = sum(leg["distance"] for leg in route_legs)
        total_duration = sum(leg["duration"] for leg in route_legs)

        logger.info(
            "Route calculated: %.2f miles, %.2f hours",
            total_distance,
            total_duration,
        )

        # =====================================================================
        # STAGE 3: HOS Compliance Calculation (50% -> 75%)
        # =====================================================================
        send_progress_update(
            trip_id,
            {
                "stage": "hos_calculation",
                "status": "processing",
                "progress": 55,
                "message": "Calculating HOS compliance...",
            },
        )

        hos_calc = HOSCalculator(trip.current_cycle_used)
        trip.update_progress(60)

        segments, daily_logs_summary = hos_calc.calculate_trip_segments(
            total_distance=total_distance,
            start_location=trip.current_location,
            pickup_location=trip.pickup_location,
            dropoff_location=trip.dropoff_location,
            route_legs=route_legs,
        )
        trip.update_progress(70)

        send_progress_update(
            trip_id,
            {
                "stage": "hos_calculation",
                "progress": 70,
                "message": "HOS compliance calculated",
            },
        )

        # =====================================================================
        # STAGE 4: Generate FMCSA Logs (75% -> 90%)
        # =====================================================================
        send_progress_update(
            trip_id,
            {
                "stage": "log_generation",
                "status": "processing",
                "progress": 75,
                "message": "Generating FMCSA-compliant logs...",
            },
        )

        total_driving_time = sum(
            s["duration"] for s in segments if s["type"] == "drive"
        )
        total_trip_time = sum(s["duration"] for s in segments)

        daily_logs = _convert_to_fmcsa_logs(
            trip_id=trip_id,
            segments=segments,
            daily_logs_summary=daily_logs_summary,
            current_location=trip.current_location,
            pickup_location=trip.pickup_location,
            dropoff_location=trip.dropoff_location,
            total_distance=total_distance,
        )
        trip.update_progress(90)

        send_progress_update(
            trip_id,
            {
                "stage": "log_generation",
                "progress": 90,
                "message": f"Generated {len(daily_logs)} daily log(s)",
            },
        )

        # =====================================================================
        # STAGE 5: Persist Results (90% -> 100%)
        # =====================================================================
        trip.total_distance = round(total_distance, 2)
        trip.total_driving_time = round(total_driving_time, 2)
        trip.total_trip_time = round(total_trip_time, 2)
        trip.route_data = {
            "segments": segments,
            "geometry": route.get("features", [{}])[0].get("geometry"),
        }
        trip.logs_data = daily_logs
        trip.status = TripCalculation.JobStatus.COMPLETED
        trip.progress = 100
        trip.save()

        logger.info("Trip %s calculation completed successfully", trip_id)

        send_progress_update(
            trip_id,
            {
                "stage": "completed",
                "status": "completed",
                "progress": 100,
                "message": "Trip calculation completed!",
                "total_distance": trip.total_distance,
                "total_driving_time": trip.total_driving_time,
                "num_days": len(daily_logs),
            },
        )

        # =====================================================================
        # TRIGGER MAP GENERATION AS SEPARATE TASK
        # =====================================================================
        map_task = generate_map_task.delay(trip_id)
        trip.map_task_id = map_task.id
        trip.map_status = TripCalculation.MapStatus.GENERATING
        trip.save(update_fields=["map_task_id", "map_status", "updated_at"])

        send_progress_update(
            trip_id,
            {
                "stage": "map_generation_queued",
                "status": "processing",
                "message": "Map generation started in background",
                "map_task_id": map_task.id,
            },
        )

        return trip_id

    except TripCalculation.DoesNotExist:
        logger.error("Trip %s not found", trip_id)
        return None

    except Exception as e:
        logger.error("Error calculating trip %s: %s", trip_id, e, exc_info=True)

        try:
            trip = TripCalculation.objects.get(id=trip_id)
            trip.status = TripCalculation.JobStatus.FAILED
            trip.error_message = str(e)
            trip.save(update_fields=["status", "error_message", "updated_at"])

            send_progress_update(
                trip_id,
                {
                    "stage": "failed",
                    "status": "failed",
                    "progress": 0,
                    "message": f"Trip calculation failed: {str(e)}",
                    "error": str(e),
                },
            )
        except Exception:
            pass

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2**self.request.retries))


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def generate_map_task(self, trip_id: int) -> Optional[str]:
    """
    Async task to generate route map image.
    This is separate from trip calculation as it can take significant time.

    Args:
        trip_id: ID of TripCalculation instance

    Returns:
        Map file path if successful, None otherwise
    """
    try:
        trip = TripCalculation.objects.get(id=trip_id)

        # Ensure trip calculation is complete
        if trip.status != TripCalculation.JobStatus.COMPLETED:
            logger.warning(
                "Cannot generate map for trip %s - calculation not complete (status: %s)",
                trip_id,
                trip.status,
            )
            return None

        trip.map_status = TripCalculation.MapStatus.GENERATING
        trip.map_progress = 10
        trip.save(update_fields=["map_status", "map_progress", "updated_at"])

        send_progress_update(
            trip_id,
            {
                "stage": "map_generation",
                "status": "generating",
                "map_progress": 10,
                "message": "Initializing map generator...",
            },
        )

        logger.info("Starting map generation for trip %s", trip_id)

        # Validate coordinates
        if not trip.coordinates:
            raise ValueError("Coordinates not available for this trip")

        current_coord = trip.coordinates.get("current", {})
        pickup_coord = trip.coordinates.get("pickup", {})
        dropoff_coord = trip.coordinates.get("dropoff", {})

        for coord, name in [
            (current_coord, "current"),
            (pickup_coord, "pickup"),
            (dropoff_coord, "dropoff"),
        ]:
            if "lat" not in coord or "lon" not in coord:
                raise ValueError(f"Invalid {name} coordinates")

        trip.map_progress = 20
        trip.save(update_fields=["map_progress", "updated_at"])

        send_progress_update(
            trip_id,
            {
                "stage": "map_generation",
                "map_progress": 20,
                "message": "Preparing map data...",
            },
        )

        # Build coordinates list
        coordinates = [
            {
                "lat": current_coord["lat"],
                "lon": current_coord["lon"],
                "name": current_coord.get("name", "Start"),
            },
            {
                "lat": pickup_coord["lat"],
                "lon": pickup_coord["lon"],
                "name": pickup_coord.get("name", "Pickup"),
            },
            {
                "lat": dropoff_coord["lat"],
                "lon": dropoff_coord["lon"],
                "name": dropoff_coord.get("name", "Dropoff"),
            },
        ]

        # Get segments and geometry
        segments = []
        geometry = None

        if trip.route_data:
            segments = trip.route_data.get("segments", [])
            geometry = trip.route_data.get("geometry")

        trip.map_progress = 40
        trip.save(update_fields=["map_progress", "updated_at"])

        send_progress_update(
            trip_id,
            {
                "stage": "map_generation",
                "map_progress": 40,
                "message": "Fetching map tiles...",
            },
        )

        # Generate map with progress callback
        generator = MapGenerator()

        def map_progress_callback(progress: int, message: str = "") -> None:
            """Callback for map generation progress updates."""
            # Scale progress from 40-90%
            scaled_progress = 40 + int(progress * 0.5)
            trip.map_progress = scaled_progress
            trip.save(update_fields=["map_progress", "updated_at"])

            send_progress_update(
                trip_id,
                {
                    "stage": "map_generation",
                    "map_progress": scaled_progress,
                    "message": message or "Generating map...",
                },
            )

        image_bytes = generator.generate_route_map(
            coordinates=coordinates,
            segments=segments,
            geometry=geometry,
            progress_callback=map_progress_callback,
        )

        trip.map_progress = 90
        trip.save(update_fields=["map_progress", "updated_at"])

        send_progress_update(
            trip_id,
            {
                "stage": "map_generation",
                "map_progress": 90,
                "message": "Saving map file...",
            },
        )

        # Save map file
        filename = f"route_map_trip_{trip_id}.png"
        trip.map_file.save(filename, ContentFile(image_bytes), save=False)
        trip.map_status = TripCalculation.MapStatus.COMPLETED
        trip.map_progress = 100
        trip.save(
            update_fields=["map_file", "map_status", "map_progress", "updated_at"]
        )

        logger.info(
            "Map generation completed for trip %s: %s", trip_id, trip.map_file.url
        )

        send_progress_update(
            trip_id,
            {
                "stage": "map_completed",
                "status": "completed",
                "map_progress": 100,
                "message": "Map generation completed!",
                "map_url": trip.map_file.url if trip.map_file else None,
            },
        )

        return trip.map_file.name

    except TripCalculation.DoesNotExist:
        logger.error("Trip %s not found for map generation", trip_id)
        return None

    except Exception as e:
        logger.error("Error generating map for trip %s: %s", trip_id, e, exc_info=True)

        try:
            trip = TripCalculation.objects.get(id=trip_id)
            trip.map_status = TripCalculation.MapStatus.FAILED
            trip.map_error_message = str(e)
            trip.save(update_fields=["map_status", "map_error_message", "updated_at"])

            send_progress_update(
                trip_id,
                {
                    "stage": "map_failed",
                    "status": "failed",
                    "map_progress": 0,
                    "message": f"Map generation failed: {str(e)}",
                    "error": str(e),
                },
            )
        except Exception:
            pass

        raise self.retry(exc=e, countdown=30 * (2**self.request.retries))


def _convert_to_fmcsa_logs(
    trip_id: int,
    segments: list[dict[str, Any]],
    daily_logs_summary: list[dict[str, Any]],
    current_location: str,
    pickup_location: str,
    dropoff_location: str,
    total_distance: float,
) -> list[dict[str, Any]]:
    """
    Convert HOS segments into FMCSA-compliant daily log format.
    """
    daily_logs: list[dict[str, Any]] = []
    base_date = datetime.now()

    # Group segments by 24-hour periods
    day_segments: list[list[dict[str, Any]]] = []
    current_day_segments: list[dict[str, Any]] = []
    cumulative_time = 0.0

    for segment in segments:
        duration = segment["duration"]

        if cumulative_time + duration > 24.0:
            time_in_current_day = 24.0 - cumulative_time

            if time_in_current_day > 0:
                current_day_segments.append(
                    {
                        **segment,
                        "start_time": cumulative_time,
                        "end_time": 24.0,
                        "duration": time_in_current_day,
                    }
                )

            day_segments.append(current_day_segments)
            current_day_segments = []

            remaining = duration - time_in_current_day
            if remaining > 0:
                current_day_segments.append(
                    {
                        **segment,
                        "start_time": 0.0,
                        "end_time": remaining,
                        "duration": remaining,
                    }
                )
                cumulative_time = remaining
            else:
                cumulative_time = 0.0
        else:
            current_day_segments.append(
                {
                    **segment,
                    "start_time": cumulative_time,
                    "end_time": cumulative_time + duration,
                    "duration": duration,
                }
            )
            cumulative_time += duration

        if cumulative_time >= 24.0:
            day_segments.append(current_day_segments)
            current_day_segments = []
            cumulative_time = 0.0

    if current_day_segments:
        day_segments.append(current_day_segments)

    # Build FMCSA logs for each day
    for day_index, day_segs in enumerate(day_segments):
        log_date = base_date + timedelta(days=day_index)

        events: list[dict[str, Any]] = []
        remarks: list[dict[str, str]] = []
        day_miles = 0.0

        day_segs.sort(key=lambda s: s["start_time"])

        day_from_address = current_location if day_index == 0 else "En route"
        day_to_address = (
            dropoff_location if day_index == len(day_segments) - 1 else "En route"
        )

        for seg in day_segs:
            seg_type = seg["type"]

            if seg_type == "start":
                continue

            if seg_type == "drive":
                status = "driving"
                day_miles += seg.get("distance", 0.0)
            elif seg_type in ["pickup", "dropoff", "fuel"]:
                status = "onDuty"
            elif seg_type == "rest":
                status = "sleeper"
            elif seg_type == "break":
                status = "offDuty"
            else:
                status = "onDuty"

            events.append(
                {
                    "start": seg["start_time"],
                    "end": seg["end_time"],
                    "status": status,
                }
            )

            location = seg.get("location", "")
            if location and location not in ["En route", "Highway"]:
                remarks.append(
                    {
                        "time": seg["start_time"],
                        "location": location,
                    }
                )

        if events and events[-1]["end"] < 24.0:
            events.append(
                {
                    "start": events[-1]["end"],
                    "end": 24.0,
                    "status": "offDuty",
                }
            )

        daily_logs.append(
            {
                "date": log_date.strftime("%m/%d/%Y"),
                "events": events,
                "total_miles": round(day_miles, 1),
                "remarks": remarks,
                "driver_name": "Michael Schumacer",
                "carrier_name": "Ferrari",
                "main_office": "Washington, D.C.",
                "co_driver": "",
                "from_address": day_from_address,
                "to_address": day_to_address,
                "home_terminal_address": "Washington, D.C.",
                "truck_number": "101",
                "shipping_doc": f"BOL-{trip_id}",
            }
        )

    return daily_logs


def send_trip_list_update(trip_id: int, status: str) -> None:
    """
    Send trip update notification to trips list WebSocket.

    Args:
        trip_id: Trip ID
        status: Current trip status
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(_async_group_send)(
                channel_layer,
                "trips_list",
                {
                    "type": "trip_updated",
                    "trip_id": trip_id,
                    "status": status,
                },
            )
    except Exception as e:
        logger.warning(f"Failed to send trips list update: {e}")
