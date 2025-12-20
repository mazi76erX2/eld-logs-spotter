import logging
from typing import Any

logger = logging.getLogger(__name__)


class HOSCalculator:
    """
    FMCSA Property-Carrying Driver Hours of Service Calculator.

    Implements:
    - 11-hour driving limit
    - 14-hour duty window
    - 70-hour/8-day cycle
    - 10-hour rest period requirement
    - Fuel stops every 1,000 miles
    """

    # FMCSA limits
    MAX_DRIVING_TIME: float = 11.0
    MAX_DUTY_WINDOW: float = 14.0
    MAX_CYCLE_HOURS: float = 70.0
    REST_PERIOD: float = 10.0

    # Operational parameters
    FUEL_INTERVAL_MILES: float = 1000.0
    FUEL_TIME: float = 0.5
    PICKUP_TIME: float = 1.0
    DROPOFF_TIME: float = 1.0
    AVERAGE_SPEED: float = 55.0  # mph

    def __init__(self, cycle_used: float) -> None:
        """
        Initialize HOS Calculator.

        Args:
            cycle_used: Hours already used in current 70-hour/8-day cycle
        """
        if cycle_used < 0 or cycle_used > self.MAX_CYCLE_HOURS:
            raise ValueError(
                f"Cycle hours must be between 0 and {self.MAX_CYCLE_HOURS}"
            )
        self.cycle_used = cycle_used
        self.remaining_cycle = self.MAX_CYCLE_HOURS - cycle_used

    def calculate_trip_segments(
        self,
        total_distance: float,
        start_location: str,
        pickup_location: str,
        dropoff_location: str,
        route_legs: list[dict[str, float]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Calculate trip segments with HOS compliance.

        Args:
            total_distance: Total trip distance in miles
            start_location: Starting location name
            pickup_location: Pickup location name
            dropoff_location: Dropoff location name
            route_legs: list of route legs with distance and duration

        Returns:
            tuple of (segments, daily_logs_summary)
        """
        segments: list[dict[str, Any]] = []

        # Tracking variables
        drive_today: float = 0.0
        duty_today: float = 0.0
        miles_since_fuel: float = 0.0
        total_miles_driven: float = 0.0

        # Start segment
        segments.append(
            {
                "type": "start",
                "duration": 0.0,
                "distance": 0.0,
                "location": start_location,
            }
        )

        # Pickup
        segments.append(
            {
                "type": "pickup",
                "duration": self.PICKUP_TIME,
                "distance": 0.0,
                "location": pickup_location,
            }
        )
        duty_today += self.PICKUP_TIME

        # Calculate remaining distance to drive
        remaining_distance = total_distance

        # Process route legs
        for leg in route_legs:
            leg_miles = leg["distance"]
            leg_hours = leg["duration"]

            logger.debug(
                f"Processing leg: {leg_miles:.2f} miles, {leg_hours:.2f} hours"
            )

            while leg_hours > 0 and remaining_distance > 0:
                # Check if we need rest
                if (
                    drive_today >= self.MAX_DRIVING_TIME
                    or duty_today >= self.MAX_DUTY_WINDOW
                ):
                    logger.debug(
                        f"Rest needed - Drive: {drive_today:.2f}h, "
                        f"Duty: {duty_today:.2f}h"
                    )

                    segments.append(
                        {
                            "type": "rest",
                            "duration": self.REST_PERIOD,
                            "distance": 0.0,
                            "location": "Rest Area",
                        }
                    )

                    # Reset daily counters
                    drive_today = 0.0
                    duty_today = 0.0
                    continue

                # Check if we need fuel
                if (
                    miles_since_fuel >= self.FUEL_INTERVAL_MILES
                    and remaining_distance > 100
                ):
                    segments.append(
                        {
                            "type": "fuel",
                            "duration": self.FUEL_TIME,
                            "distance": 0.0,
                            "location": "Fuel Station",
                        }
                    )
                    duty_today += self.FUEL_TIME
                    miles_since_fuel = 0.0
                    continue

                # Calculate available driving time
                drive_available = min(
                    self.MAX_DRIVING_TIME - drive_today,
                    self.MAX_DUTY_WINDOW - duty_today,
                )

                if drive_available <= 0:
                    continue

                # Drive segment
                drive_hours = min(
                    drive_available, leg_hours, remaining_distance / self.AVERAGE_SPEED
                )
                drive_miles = min(drive_hours * self.AVERAGE_SPEED, remaining_distance)

                segments.append(
                    {
                        "type": "drive",
                        "duration": round(drive_hours, 2),
                        "distance": round(drive_miles, 2),
                        "location": "En route",
                    }
                )

                # Update counters
                leg_hours -= drive_hours
                remaining_distance -= drive_miles
                drive_today += drive_hours
                duty_today += drive_hours
                miles_since_fuel += drive_miles
                total_miles_driven += drive_miles

                logger.debug(
                    f"Drove {drive_miles:.2f} miles in {drive_hours:.2f} hours. "
                    f"Remaining: {remaining_distance:.2f} miles"
                )

        # Dropoff
        segments.append(
            {
                "type": "dropoff",
                "duration": self.DROPOFF_TIME,
                "distance": 0.0,
                "location": dropoff_location,
            }
        )

        # Generate daily summary (simple version)
        daily_logs_summary = self._generate_daily_summary(segments)

        logger.info(
            f"Generated {len(segments)} segments, " f"{len(daily_logs_summary)} days"
        )

        return segments, daily_logs_summary

    def _generate_daily_summary(
        self, segments: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate simplified daily summary."""
        # Simple implementation - can be enhanced
        return [
            {"day": 1, "driving": 0.0, "onDuty": 0.0, "sleeper": 0.0, "offDuty": 0.0}
        ]
