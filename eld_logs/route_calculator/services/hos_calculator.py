import logging
from typing import Any

logger = logging.getLogger(__name__)


class HOSCalculator:
    """
    FMCSA Property-Carrying Driver Hours of Service Calculator.

    Implements:
    - 11-hour driving limit (per duty period)
    - 14-hour duty window (from start of duty)
    - 30-minute break required after 8 hours of driving
    - 70-hour/8-day cycle limit
    - 10-hour rest period requirement (resets 11/14 hour clocks)
    - Fuel stops every 1,000 miles
    - 1 hour for pickup and dropoff

    No adverse driving conditions assumed.
    """

    # FMCSA Property-Carrying Driver Limits
    MAX_DRIVING_TIME: float = 11.0  # Max driving hours per duty period
    MAX_DUTY_WINDOW: float = 14.0  # Max on-duty window from start
    MAX_DRIVING_BEFORE_BREAK: float = 8.0  # Must take 30-min break after 8 hrs driving
    BREAK_DURATION: float = 0.5  # 30-minute break
    MAX_CYCLE_HOURS: float = 70.0  # 70-hour/8-day cycle
    REST_PERIOD: float = 10.0  # 10-hour rest requirement

    # Operational parameters
    FUEL_INTERVAL_MILES: float = 1000.0  # Fuel stop every 1,000 miles
    FUEL_TIME: float = 0.5  # 30 minutes for fueling
    PICKUP_TIME: float = 1.0  # 1 hour for pickup
    DROPOFF_TIME: float = 1.0  # 1 hour for dropoff
    AVERAGE_SPEED: float = 55.0  # Average speed in mph

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
        Calculate trip segments with full FMCSA HOS compliance.

        Args:
            total_distance: Total trip distance in miles
            start_location: Starting location name
            pickup_location: Pickup location name
            dropoff_location: Dropoff location name
            route_legs: List of route legs with distance and duration

        Returns:
            Tuple of (segments, daily_logs_summary)
        """
        segments: list[dict[str, Any]] = []

        # Daily tracking variables (reset after 10-hour rest)
        drive_today: float = 0.0  # Driving hours in current duty period
        duty_today: float = 0.0  # Total duty hours in current duty period
        drive_since_break: float = 0.0  # Driving hours since last 30-min break

        # Trip tracking variables
        miles_since_fuel: float = 0.0
        total_miles_driven: float = 0.0
        cycle_hours_used: float = self.cycle_used

        # Start segment
        segments.append(
            {
                "type": "start",
                "duration": 0.0,
                "distance": 0.0,
                "location": start_location,
            }
        )

        # Pickup (counts as on-duty time)
        segments.append(
            {
                "type": "pickup",
                "duration": self.PICKUP_TIME,
                "distance": 0.0,
                "location": pickup_location,
            }
        )
        duty_today += self.PICKUP_TIME
        cycle_hours_used += self.PICKUP_TIME

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
                # Check 1: Do we need a 10-hour rest? (11-hour driving or 14-hour window exceeded)
                if (
                    drive_today >= self.MAX_DRIVING_TIME
                    or duty_today >= self.MAX_DUTY_WINDOW
                ):
                    logger.debug(
                        f"10-hour rest needed - Drive: {drive_today:.2f}h, "
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

                    # Reset daily counters after 10-hour rest
                    drive_today = 0.0
                    duty_today = 0.0
                    drive_since_break = 0.0
                    continue

                # Check 2: Do we need a 30-minute break? (8 hours driving since last break)
                if drive_since_break >= self.MAX_DRIVING_BEFORE_BREAK:
                    logger.debug(
                        f"30-minute break needed - Driving since break: {drive_since_break:.2f}h"
                    )

                    segments.append(
                        {
                            "type": "break",
                            "duration": self.BREAK_DURATION,
                            "distance": 0.0,
                            "location": "Rest Stop",
                        }
                    )

                    # Break counts toward 14-hour window but resets 8-hour driving clock
                    duty_today += self.BREAK_DURATION
                    drive_since_break = 0.0
                    continue

                # Check 3: Do we need fuel? (every 1,000 miles)
                if (
                    miles_since_fuel >= self.FUEL_INTERVAL_MILES
                    and remaining_distance > 100
                ):
                    logger.debug(
                        f"Fuel stop needed - Miles since fuel: {miles_since_fuel:.2f}"
                    )

                    segments.append(
                        {
                            "type": "fuel",
                            "duration": self.FUEL_TIME,
                            "distance": 0.0,
                            "location": "Fuel Station",
                        }
                    )
                    duty_today += self.FUEL_TIME
                    cycle_hours_used += self.FUEL_TIME
                    miles_since_fuel = 0.0
                    continue

                # Check 4: 70-hour cycle limit
                if cycle_hours_used >= self.MAX_CYCLE_HOURS:
                    logger.debug(
                        f"70-hour cycle limit reached: {cycle_hours_used:.2f}h"
                    )

                    # Need a 34-hour restart (simplified as extended rest)
                    segments.append(
                        {
                            "type": "rest",
                            "duration": 34.0,  # 34-hour restart
                            "distance": 0.0,
                            "location": "Rest Area - 34hr Restart",
                        }
                    )

                    # Reset all counters
                    drive_today = 0.0
                    duty_today = 0.0
                    drive_since_break = 0.0
                    cycle_hours_used = 0.0
                    continue

                # Calculate available driving time (most restrictive limit)
                drive_available = min(
                    self.MAX_DRIVING_TIME - drive_today,  # 11-hour limit
                    self.MAX_DUTY_WINDOW - duty_today,  # 14-hour window
                    self.MAX_DRIVING_BEFORE_BREAK
                    - drive_since_break,  # 8-hour break rule
                    self.MAX_CYCLE_HOURS - cycle_hours_used,  # 70-hour cycle
                )

                if drive_available <= 0:
                    continue

                # Calculate this drive segment
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

                # Update all counters
                leg_hours -= drive_hours
                remaining_distance -= drive_miles
                drive_today += drive_hours
                duty_today += drive_hours
                drive_since_break += drive_hours
                cycle_hours_used += drive_hours
                miles_since_fuel += drive_miles
                total_miles_driven += drive_miles

                logger.debug(
                    f"Drove {drive_miles:.2f} miles in {drive_hours:.2f} hours. "
                    f"Remaining: {remaining_distance:.2f} miles. "
                    f"Drive today: {drive_today:.2f}h, Since break: {drive_since_break:.2f}h"
                )

        # Dropoff (counts as on-duty time)
        segments.append(
            {
                "type": "dropoff",
                "duration": self.DROPOFF_TIME,
                "distance": 0.0,
                "location": dropoff_location,
            }
        )

        # Generate daily summary
        daily_logs_summary = self._generate_daily_summary(segments)

        logger.info(
            f"Generated {len(segments)} segments, {len(daily_logs_summary)} days. "
            f"Total distance: {total_miles_driven:.2f} miles"
        )

        return segments, daily_logs_summary

    def _generate_daily_summary(
        self, segments: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Generate daily summary from segments.

        Groups segments into 24-hour periods and calculates totals.
        """
        daily_summaries: list[dict[str, Any]] = []

        current_day = 1
        day_driving = 0.0
        day_on_duty = 0.0
        day_sleeper = 0.0
        day_off_duty = 0.0
        day_time = 0.0

        for segment in segments:
            seg_type = segment["type"]
            duration = segment["duration"]

            # Check if this segment crosses into next day
            while day_time + duration > 24.0:
                # Fill remaining time in current day
                remaining_today = 24.0 - day_time

                if seg_type == "drive":
                    day_driving += remaining_today
                elif seg_type in ["pickup", "dropoff", "fuel"]:
                    day_on_duty += remaining_today
                elif seg_type == "rest":
                    day_sleeper += remaining_today
                elif seg_type == "break":
                    day_off_duty += remaining_today

                # Save current day
                daily_summaries.append(
                    {
                        "day": current_day,
                        "driving": round(day_driving, 2),
                        "onDuty": round(day_on_duty, 2),
                        "sleeper": round(day_sleeper, 2),
                        "offDuty": round(day_off_duty, 2),
                    }
                )

                # Start new day
                current_day += 1
                day_driving = 0.0
                day_on_duty = 0.0
                day_sleeper = 0.0
                day_off_duty = 0.0
                day_time = 0.0
                duration -= remaining_today

            # Add to current day
            if seg_type == "drive":
                day_driving += duration
            elif seg_type in ["pickup", "dropoff", "fuel"]:
                day_on_duty += duration
            elif seg_type == "rest":
                day_sleeper += duration
            elif seg_type == "break":
                day_off_duty += duration

            day_time += duration

        # Don't forget the last day
        if day_time > 0:
            # Fill rest of day with off-duty
            remaining = 24.0 - day_time
            day_off_duty += remaining

            daily_summaries.append(
                {
                    "day": current_day,
                    "driving": round(day_driving, 2),
                    "onDuty": round(day_on_duty, 2),
                    "sleeper": round(day_sleeper, 2),
                    "offDuty": round(day_off_duty, 2),
                }
            )

        return daily_summaries
