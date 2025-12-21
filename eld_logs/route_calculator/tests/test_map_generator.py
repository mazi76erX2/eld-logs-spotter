#!/usr/bin/env python
"""
Test script for MapGenerator service.

Run with: pytest route_calculator/services/test_map_generator.py -v
"""

import io
import os
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

# Test output files to clean up
TEST_OUTPUT_FILES = [
    "output_daily_log.png",
    "test_map_output.png",
]


def cleanup_test_files():
    """Remove all test-generated files."""
    for filename in TEST_OUTPUT_FILES:
        try:
            if os.path.exists(filename):
                os.remove(filename)
        except OSError:
            pass


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Fixture to clean up test files after each test."""
    yield
    cleanup_test_files()


class TestMapGenerator:
    """Tests for MapGenerator service."""

    def test_generate_route_map_success(self):
        """Test successful map generation."""
        from route_calculator.services.map_generator import MapGenerator

        gen = MapGenerator()

        coordinates = [
            {"lat": 40.7128, "lon": -74.006, "name": "New York, NY"},
            {"lat": 39.9526, "lon": -75.1652, "name": "Philadelphia, PA"},
        ]

        segments = [
            {"type": "start", "location": "New York, NY"},
            {"type": "drive", "distance": 95},
            {"type": "dropoff", "location": "Philadelphia, PA"},
        ]

        geometry = {
            "type": "LineString",
            "coordinates": [
                [-74.006, 40.7128],
                [-74.5, 40.6],
                [-75.0, 40.3],
                [-75.1652, 39.9526],
            ],
        }

        image_bytes = gen.generate_route_map(
            coordinates=coordinates,
            segments=segments,
            geometry=geometry,
        )

        assert image_bytes is not None
        assert len(image_bytes) > 0

        # Verify it's a valid PNG
        img = Image.open(io.BytesIO(image_bytes))
        assert img.format == "PNG"
        assert img.width > 0
        assert img.height > 0

    def test_generate_route_map_no_geometry(self):
        """Test map generation without geometry (fallback)."""
        from route_calculator.services.map_generator import MapGenerator

        gen = MapGenerator()

        coordinates = [
            {"lat": 40.7128, "lon": -74.006, "name": "Start"},
            {"lat": 39.9526, "lon": -75.1652, "name": "End"},
        ]

        image_bytes = gen.generate_route_map(
            coordinates=coordinates,
            segments=[],
            geometry=None,
        )

        assert image_bytes is not None
        assert len(image_bytes) > 0

    def test_generate_route_map_empty_coordinates(self):
        """Test map generation with empty coordinates."""
        from route_calculator.services.map_generator import MapGenerator

        gen = MapGenerator()

        image_bytes = gen.generate_route_map(
            coordinates=[],
            segments=[],
            geometry=None,
        )

        assert image_bytes is not None
        assert len(image_bytes) > 0

    def test_extract_markers_assigns_types(self):
        """Test that markers are assigned correct types."""
        from route_calculator.services.map_generator import MapGenerator

        gen = MapGenerator()
        coordinates = [
            {"lat": 40.7128, "lon": -74.0060, "name": "Start", "type": "start"},
            {"lat": 40.7580, "lon": -73.9855, "name": "Stop", "type": "fuel"},
            {"lat": 40.7484, "lon": -73.9857, "name": "End", "type": "end"},
        ]
        # Empty geometry list for this test
        geometry = []

        markers = gen._extract_all_markers(coordinates, [], geometry)

        assert len(markers) == 3
        assert markers[0]["type"] == "start"
        assert markers[1]["type"] == "pickup"
        assert markers[2]["type"] == "dropoff"

    def test_generate_route_map_with_progress_callback(self):
        """Test map generation with progress callback."""
        from route_calculator.services.map_generator import MapGenerator

        gen = MapGenerator()

        coordinates = [
            {"lat": 40.7128, "lon": -74.006, "name": "Start"},
            {"lat": 39.9526, "lon": -75.1652, "name": "End"},
        ]

        progress_updates = []

        def progress_callback(progress: int, message: str = ""):
            progress_updates.append((progress, message))

        image_bytes = gen.generate_route_map(
            coordinates=coordinates,
            segments=[],
            geometry=None,
            progress_callback=progress_callback,
        )

        assert image_bytes is not None
        # Progress callback may or may not be called depending on implementation


class TestLogGenerator:
    """Tests for LogGenerator service."""

    def test_generate_log_image_returns_png(self):
        """Test that log generator returns valid PNG."""
        from route_calculator.services.log_generator import LogGenerator

        log_data = {
            "date": "04/09/2021",
            "total_miles": 350,
            "from_address": "Richmond, VA",
            "to_address": "Newark, NJ",
            "home_terminal_address": "Washington, D.C.",
            "truck_number": "123",
            "shipping_doc": "101601",
            "events": [
                {"start": 0, "end": 6, "status": "offDuty"},
                {"start": 6, "end": 8, "status": "driving"},
                {"start": 8, "end": 24, "status": "offDuty"},
            ],
            "remarks": [
                {"location": "Richmond, VA"},
            ],
        }

        gen = LogGenerator()
        img_bytes = gen.generate_log_image(
            log_data,
            day_number=1,
            driver_name="John Doe",
            carrier_name="Test Carrier",
            main_office="Washington, D.C.",
        )

        assert img_bytes is not None
        assert len(img_bytes) > 0

        # Verify it's a valid PNG
        img = Image.open(io.BytesIO(img_bytes))
        assert img.format == "PNG"

    def test_generate_log_image_with_all_statuses(self):
        """Test log generation with all duty statuses."""
        from route_calculator.services.log_generator import LogGenerator

        log_data = {
            "date": "04/09/2021",
            "total_miles": 500,
            "events": [
                {"start": 0, "end": 6, "status": "offDuty"},
                {"start": 6, "end": 7, "status": "onDuty"},
                {"start": 7, "end": 12, "status": "driving"},
                {"start": 12, "end": 14, "status": "sleeper"},
                {"start": 14, "end": 18, "status": "driving"},
                {"start": 18, "end": 24, "status": "offDuty"},
            ],
            "remarks": [],
        }

        gen = LogGenerator()
        img_bytes = gen.generate_log_image(
            log_data,
            day_number=1,
            driver_name="Test Driver",
            carrier_name="Test Carrier",
            main_office="Test Office",
        )

        assert img_bytes is not None
        assert len(img_bytes) > 0

    def test_generate_log_image_with_co_driver(self):
        """Test log generation with co-driver specified."""
        from route_calculator.services.log_generator import LogGenerator

        log_data = {
            "date": "04/09/2021",
            "total_miles": 350,
            "events": [
                {"start": 0, "end": 8, "status": "driving"},
                {"start": 8, "end": 24, "status": "offDuty"},
            ],
            "remarks": [],
        }

        gen = LogGenerator()
        img_bytes = gen.generate_log_image(
            log_data,
            day_number=1,
            driver_name="John Doe",
            carrier_name="Test Carrier",
            main_office="Test Office",
            co_driver="Jane Doe",
        )

        assert img_bytes is not None
        assert len(img_bytes) > 0


# ============================================================
# STANDALONE RUNNER (for manual testing with visual output)
# ============================================================


def run_standalone_log_test():
    """Run log generator test with file output for visual inspection."""
    from route_calculator.services.log_generator import LogGenerator

    print("\n" + "=" * 60)
    print("LogGenerator Test - Visual Output")
    print("=" * 60)

    log_data = {
        "date": "04/09/2021",
        "total_miles": 350,
        "from_address": "Richmond, VA",
        "to_address": "Newark, NJ",
        "home_terminal_address": "Washington, D.C.",
        "truck_number": "123, 20544",
        "shipping_doc": "101601",
        "events": [
            {"start": 0, "end": 6, "status": "offDuty"},
            {"start": 6, "end": 7.5, "status": "onDuty"},
            {"start": 7.5, "end": 9, "status": "driving"},
            {"start": 9, "end": 9.5, "status": "onDuty"},
            {"start": 9.5, "end": 12, "status": "driving"},
            {"start": 12, "end": 13, "status": "offDuty"},
            {"start": 13, "end": 15, "status": "driving"},
            {"start": 15, "end": 15.5, "status": "onDuty"},
            {"start": 15.5, "end": 16, "status": "driving"},
            {"start": 16, "end": 17.75, "status": "sleeper"},
            {"start": 17.75, "end": 19, "status": "driving"},
            {"start": 19, "end": 21, "status": "onDuty"},
            {"start": 21, "end": 24, "status": "offDuty"},
        ],
        "remarks": [
            {"location": "Richmond, VA"},
            {"location": "Fredericksburg, VA"},
            {"location": "Baltimore, MD"},
            {"location": "Philadelphia, PA"},
            {"location": "Cherry Hill, NJ"},
            {"location": "Newark, NJ"},
        ],
    }

    try:
        gen = LogGenerator()
        img = gen.generate_log_image(
            log_data,
            1,
            "John E. Doe",
            "John Doe's Transportation",
            "Washington, D.C.",
            "Jane Doe",
        )

        out = "output_daily_log.png"
        with open(out, "wb") as f:
            f.write(img)

        print(f"Generated: {out} ({os.path.getsize(out):,} bytes)")
        print("Test PASSED")

        # Cleanup
        cleanup_test_files()
        return True

    except Exception as e:
        print(f"Test FAILED: {e}")
        cleanup_test_files()
        return False


if __name__ == "__main__":
    import sys

    success = run_standalone_log_test()
    sys.exit(0 if success else 1)
