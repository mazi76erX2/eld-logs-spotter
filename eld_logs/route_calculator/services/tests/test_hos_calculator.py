from ..services.hos_calculator import HOSCalculator


def test_hos_calculation_basic_trip():
    hos = HOSCalculator(cycle_used=10)

    segments, summary = hos.calculate_trip_segments(
        total_distance=300,
        start_location="Dallas, TX",
        pickup_location="Houston, TX",
        dropoff_location="Austin, TX",
        route_legs=[{"distance": 300, "duration": 6}],
    )

    assert segments
    assert any(s["type"] == "drive" for s in segments)

    total_drive_time = sum(s["duration"] for s in segments if s["type"] == "drive")

    assert total_drive_time <= hos.MAX_DRIVING_TIME
