import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from celery import shared_task

from .models import TripCalculation
from .services.hos_calculator import HOSCalculator
from .services.route_service import RouteService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def calculate_trip_task(self, trip_id: int) -> Optional[int]:
    """
    Async task to calculate trip route and generate FMCSA-compliant logs.

    Args:
        trip_id: ID of TripCalculation instance

    Returns:
        Trip ID if successful, None otherwise
    """
    try:
        trip = TripCalculation.objects.get(id=trip_id)
        trip.status = TripCalculation.JobStatus.PROCESSING
        trip.save()

        logger.info("Starting calculation for trip %s", trip_id)

        # Initialize services
        route_service = RouteService()

        # Geocode locations
        current_coord = route_service.geocode_location(trip.current_location)
        pickup_coord = route_service.geocode_location(trip.pickup_location)
        dropoff_coord = route_service.geocode_location(trip.dropoff_location)

        if not all([current_coord, pickup_coord, dropoff_coord]):
            raise ValueError("Could not geocode one or more locations")

        # Store coordinates
        trip.coordinates = {
            "current": current_coord,
            "pickup": pickup_coord,
            "dropoff": dropoff_coord,
        }
        trip.save()

        # Build coordinates for routing
        coordinates = [
            [current_coord["lon"], current_coord["lat"]],
            [pickup_coord["lon"], pickup_coord["lat"]],
            [dropoff_coord["lon"], dropoff_coord["lat"]],
        ]

        # Get route
        route = route_service.get_route(coordinates)
        if not route:
            raise ValueError("Could not calculate route")

        # Extract route legs
        route_legs = route_service.get_route_legs(route)
        if not route_legs:
            raise ValueError("No route legs found")

        # Calculate totals
        total_distance = sum(leg["distance"] for leg in route_legs)
        total_duration = sum(leg["duration"] for leg in route_legs)

        logger.info(
            "Route calculated: %.2f miles, %.2f hours",
            total_distance,
            total_duration,
        )

        # Calculate HOS compliance
        hos_calc = HOSCalculator(trip.current_cycle_used)

        segments, daily_logs_summary = hos_calc.calculate_trip_segments(
            total_distance=total_distance,
            start_location=trip.current_location,
            pickup_location=trip.pickup_location,
            dropoff_location=trip.dropoff_location,
            route_legs=route_legs,
        )

        # Calculate totals from segments
        total_driving_time = sum(
            s["duration"] for s in segments if s["type"] == "drive"
        )
        total_trip_time = sum(s["duration"] for s in segments)

        # Convert to FMCSA logs
        daily_logs = _convert_to_fmcsa_logs(
            trip_id=trip_id,  # Pass trip_id
            segments=segments,
            daily_logs_summary=daily_logs_summary,
            current_location=trip.current_location,
            pickup_location=trip.pickup_location,
            dropoff_location=trip.dropoff_location,
            total_distance=total_distance,
        )

        # Persist results
        trip.total_distance = round(total_distance, 2)
        trip.total_driving_time = round(total_driving_time, 2)
        trip.total_trip_time = round(total_trip_time, 2)
        trip.route_data = {
            "segments": segments,
            "geometry": route.get("features", [{}])[0].get("geometry"),
        }
        trip.logs_data = daily_logs
        trip.status = TripCalculation.JobStatus.COMPLETED
        trip.save()

        logger.info("Trip %s calculation completed successfully", trip_id)
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
            trip.save()
        except Exception:
            pass

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60)


def _convert_to_fmcsa_logs(
    trip_id: int,  # Added trip_id parameter
    segments: list[dict[str, Any]],
    daily_logs_summary: list[dict[str, Any]],
    current_location: str,
    pickup_location: str,
    dropoff_location: str,
    total_distance: float,
) -> list[dict[str, Any]]:
    """
    Convert HOS segments into FMCSA-compliant daily log format.

    Each log must contain:
    - events: list of duty status changes with start/end times
    - date: date of the log
    - total_miles: miles driven that day
    - remarks: location changes
    """
    daily_logs: list[dict[str, Any]] = []
    base_date = datetime.now()

    # Group segments by 24-hour periods
    day_segments: list[list[dict[str, Any]]] = []
    current_day_segments: list[dict[str, Any]] = []
    cumulative_time = 0.0

    for segment in segments:
        duration = segment["duration"]

        # Check if segment crosses midnight
        if cumulative_time + duration > 24.0:
            time_in_current_day = 24.0 - cumulative_time

            if time_in_current_day > 0:
                # Add portion to current day
                current_day_segments.append(
                    {
                        **segment,
                        "start_time": cumulative_time,
                        "end_time": 24.0,
                        "duration": time_in_current_day,
                    }
                )

            # Save current day
            day_segments.append(current_day_segments)
            current_day_segments = []

            # Add remainder to next day
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
            # Segment fits in current day
            current_day_segments.append(
                {
                    **segment,
                    "start_time": cumulative_time,
                    "end_time": cumulative_time + duration,
                    "duration": duration,
                }
            )
            cumulative_time += duration

        # Check if we've completed a 24-hour period
        if cumulative_time >= 24.0:
            day_segments.append(current_day_segments)
            current_day_segments = []
            cumulative_time = 0.0

    # Add remaining segments
    if current_day_segments:
        day_segments.append(current_day_segments)

    # Build FMCSA logs for each day
    for day_index, day_segs in enumerate(day_segments):
        log_date = base_date + timedelta(days=day_index)

        events: list[dict[str, Any]] = []
        remarks: list[dict[str, str]] = []
        day_miles = 0.0

        # Sort segments by start time
        day_segs.sort(key=lambda s: s["start_time"])

        # Determine from/to addresses for this day
        day_from_address = current_location if day_index == 0 else "En route"
        day_to_address = (
            dropoff_location if day_index == len(day_segments) - 1 else "En route"
        )

        for seg in day_segs:
            seg_type = seg["type"]

            # Skip start markers
            if seg_type == "start":
                continue

            # Map segment type to duty status
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

            # Add event
            events.append(
                {
                    "start": seg["start_time"],
                    "end": seg["end_time"],
                    "status": status,
                }
            )

            # Add location remark for significant events
            location = seg.get("location", "")
            if location and location not in ["En route", "Highway"]:
                remarks.append(
                    {
                        "time": seg["start_time"],
                        "location": location,
                    }
                )

        # Ensure 24-hour coverage - fill remaining time with off-duty
        if events and events[-1]["end"] < 24.0:
            events.append(
                {
                    "start": events[-1]["end"],
                    "end": 24.0,
                    "status": "offDuty",
                }
            )

        # Create daily log entry with all required fields
        daily_logs.append(
            {
                "date": log_date.strftime("%m/%d/%Y"),
                "events": events,
                "total_miles": round(day_miles, 1),
                "remarks": remarks,
                "driver_name": "Driver Name",
                "carrier_name": "Carrier Name",
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
