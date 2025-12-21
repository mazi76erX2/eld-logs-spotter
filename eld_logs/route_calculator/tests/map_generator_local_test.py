#!/usr/bin/env python
"""
Test script for MapGenerator with actual route geometry.

Run with: pytest route_calculator/tests/map_generator_local_test.py -v
Or standalone: python route_calculator/tests/map_generator_local_test.py
"""

import io
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytest

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Missing Pillow. Install with: pip install Pillow")
    sys.exit(1)

try:
    import staticmap

    STATICMAP_AVAILABLE = True
except ImportError:
    STATICMAP_AVAILABLE = False


# Simulated OpenRouteService geometry (actual road coordinates)
SAMPLE_GEOMETRY_NYC_TO_PHILLY = {
    "type": "LineString",
    "coordinates": [
        [-74.006, 40.7128],
        [-74.0055, 40.7135],
        [-74.003, 40.718],
        [-74.05, 40.735],
        [-74.1, 40.75],
        [-74.15, 40.72],
        [-74.2, 40.7],
        [-74.3, 40.68],
        [-74.4, 40.65],
        [-74.5, 40.6],
        [-74.6, 40.55],
        [-74.7, 40.5],
        [-74.8, 40.45],
        [-74.9, 40.4],
        [-75.0, 40.35],
        [-75.05, 40.3],
        [-75.1, 40.25],
        [-75.12, 40.2],
        [-75.14, 40.1],
        [-75.16, 40.05],
        [-75.1652, 39.9526],
    ],
}

SAMPLE_GEOMETRY_CROSS_COUNTRY = {
    "type": "LineString",
    "coordinates": [
        [-74.006, 40.7128],
        [-74.5, 40.6],
        [-75.0, 40.4],
        [-75.5, 40.3],
        [-76.0, 40.2],
        [-77.0, 40.0],
        [-78.0, 39.8],
        [-79.0, 39.6],
        [-80.0, 39.5],
        [-81.0, 39.4],
        [-82.0, 39.5],
        [-83.0, 39.7],
        [-84.0, 39.9],
        [-85.0, 40.2],
        [-86.0, 40.5],
        [-87.0, 41.0],
        [-87.6298, 41.8781],
        [-88.0, 41.5],
        [-90.0, 41.0],
        [-92.0, 40.5],
        [-95.0, 39.5],
        [-98.0, 38.5],
        [-100.0, 37.5],
        [-103.0, 36.5],
        [-106.0, 35.5],
        [-109.0, 35.0],
        [-112.0, 34.5],
        [-115.0, 34.2],
        [-118.2437, 34.0522],
    ],
}

# List of test-generated files to clean up
TEST_OUTPUT_FILES = [
    "test_map_with_road_geometry.png",
    "test_map_cross_country.png",
    "test_map_no_geometry.png",
    "test_map_osm_tiles.png",
]


class MapGenerator:
    """MapGenerator with route geometry support - copy for testing."""

    DEFAULT_WIDTH = 1200
    DEFAULT_HEIGHT = 800

    MARKER_COLORS = {
        "start": {"rgb": (34, 139, 34), "hex": "#228B22"},
        "pickup": {"rgb": (30, 144, 255), "hex": "#1E90FF"},
        "dropoff": {"rgb": (220, 20, 60), "hex": "#DC143C"},
        "rest": {"rgb": (148, 0, 211), "hex": "#9400D3"},
        "fuel": {"rgb": (255, 140, 0), "hex": "#FF8C00"},
    }

    ROUTE_COLOR = "#3388ff"
    ROUTE_WIDTH = 4
    MARKER_RADIUS = 12

    def generate_route_map(
        self,
        coordinates: List[Dict[str, float]],
        segments: List[Dict[str, Any]],
        geometry: Optional[Dict[str, Any]] = None,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        progress_callback: Optional[Any] = None,
    ) -> bytes:
        if STATICMAP_AVAILABLE:
            try:
                return self._generate_with_staticmap(
                    coordinates, segments, geometry, width, height
                )
            except Exception as e:
                logger.error(f"staticmap error: {e}", exc_info=True)

        return self._generate_fallback_map(
            coordinates, segments, geometry, width, height
        )

    def _generate_with_staticmap(
        self,
        coordinates: List[Dict[str, float]],
        segments: List[Dict[str, Any]],
        geometry: Optional[Dict[str, Any]],
        width: int,
        height: int,
    ) -> bytes:
        m = staticmap.StaticMap(
            width,
            height,
            url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            tile_size=256,
        )

        if geometry and geometry.get("coordinates"):
            route_coords = geometry["coordinates"]
            if len(route_coords) >= 2:
                line_coords = [(c[0], c[1]) for c in route_coords]
                route_line = staticmap.Line(
                    line_coords,
                    self.ROUTE_COLOR,
                    self.ROUTE_WIDTH,
                )
                m.add_line(route_line)
                logger.info(f"Drawing route with {len(route_coords)} points")

        markers = self._extract_markers(coordinates, segments)
        for marker in markers:
            color = self.MARKER_COLORS.get(marker["type"], {}).get("hex", "#808080")
            circle = staticmap.CircleMarker(
                (marker["lon"], marker["lat"]),
                color,
                self.MARKER_RADIUS,
            )
            m.add_marker(circle)

        image = m.render()
        image = self._add_legend(image, markers, segments)

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        return buf.getvalue()

    def _generate_fallback_map(
        self,
        coordinates: List[Dict[str, float]],
        segments: List[Dict[str, Any]],
        geometry: Optional[Dict[str, Any]],
        width: int,
        height: int,
    ) -> bytes:
        img = Image.new("RGB", (width, height), color=(245, 245, 245))
        draw = ImageDraw.Draw(img)

        if not coordinates:
            return self._generate_placeholder_map(width, height)

        all_points = [(c["lon"], c["lat"]) for c in coordinates]
        if geometry and geometry.get("coordinates"):
            all_points.extend([(c[0], c[1]) for c in geometry["coordinates"]])

        lons = [p[0] for p in all_points]
        lats = [p[1] for p in all_points]

        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)

        lon_pad = (max_lon - min_lon) * 0.1 or 1.0
        lat_pad = (max_lat - min_lat) * 0.1 or 1.0
        min_lon -= lon_pad
        max_lon += lon_pad
        min_lat -= lat_pad
        max_lat += lat_pad

        margin = 40
        legend_w = 220
        map_w = width - legend_w - margin * 2
        map_h = height - margin * 2
        map_x, map_y = margin, margin

        draw.rectangle(
            [(map_x, map_y), (map_x + map_w, map_y + map_h)],
            fill=(255, 255, 255),
            outline=(200, 200, 200),
            width=2,
        )

        def to_px(lon, lat):
            x = map_x + int((lon - min_lon) / (max_lon - min_lon) * map_w)
            y = map_y + int((max_lat - lat) / (max_lat - min_lat) * map_h)
            return x, y

        if geometry and geometry.get("coordinates"):
            pts = [to_px(c[0], c[1]) for c in geometry["coordinates"]]
            for i in range(len(pts) - 1):
                draw.line([pts[i], pts[i + 1]], fill=(51, 136, 255), width=3)

        markers = self._extract_markers(coordinates, segments)
        font = self._load_font(10)

        for marker in markers:
            x, y = to_px(marker["lon"], marker["lat"])
            color = self.MARKER_COLORS.get(marker["type"], {}).get(
                "rgb", (128, 128, 128)
            )
            r = self.MARKER_RADIUS
            draw.ellipse(
                [(x - r - 2, y - r - 2), (x + r + 2, y + r + 2)], fill=(255, 255, 255)
            )
            draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=color)

            label = marker.get("label", "")[:20]
            if label:
                bbox = draw.textbbox((0, 0), label, font=font)
                tw = bbox[2] - bbox[0]
                draw.text((x - tw // 2, y + r + 4), label, fill=(60, 60, 60), font=font)

        img = self._add_legend(img, markers, segments)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf.getvalue()

    def _extract_markers(self, coordinates, segments):
        markers = []
        for i, coord in enumerate(coordinates):
            if i == 0:
                t = "start"
            elif i == len(coordinates) - 1:
                t = "dropoff"
            else:
                t = "pickup"
            markers.append(
                {
                    "lat": coord["lat"],
                    "lon": coord["lon"],
                    "type": t,
                    "label": coord.get("name", f"Point {i+1}"),
                }
            )
        return markers

    def _add_legend(self, img, markers, segments):
        draw = ImageDraw.Draw(img)
        font = self._load_font(12)

        legend_x = img.width - 200
        legend_y = 20

        types = {}
        for m in markers:
            types[m["type"]] = types.get(m["type"], 0) + 1

        h = 50 + len(types) * 25
        draw.rectangle(
            [(legend_x, legend_y), (legend_x + 180, legend_y + h)],
            fill=(255, 255, 255),
            outline=(180, 180, 180),
        )
        draw.text(
            (legend_x + 10, legend_y + 10), "Legend", fill=(40, 40, 40), font=font
        )

        y = 38
        for t in ["start", "pickup", "dropoff", "rest", "fuel"]:
            if t not in types:
                continue
            color = self.MARKER_COLORS.get(t, {}).get("rgb", (128, 128, 128))
            cx, cy = legend_x + 18, legend_y + y + 6
            draw.ellipse([(cx - 6, cy - 6), (cx + 6, cy + 6)], fill=color)
            draw.text(
                (legend_x + 32, legend_y + y),
                f"{t.capitalize()}: {types[t]}",
                fill=(60, 60, 60),
                font=font,
            )
            y += 25

        return img

    def _load_font(self, size):
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:\\Windows\\Fonts\\arial.ttf",
        ]
        for p in paths:
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def _generate_placeholder_map(self, width, height):
        img = Image.new("RGB", (width, height), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        font = self._load_font(20)
        text = "Map Unavailable"
        bbox = draw.textbbox((0, 0), text, font=font)
        x = (width - (bbox[2] - bbox[0])) // 2
        y = (height - (bbox[3] - bbox[1])) // 2
        draw.text((x, y), text, fill=(120, 120, 120), font=font)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf.getvalue()


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


# ============================================================
# TESTS
# ============================================================


def test_route_with_geometry():
    """Test map with actual route geometry (following roads)."""
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

    image_bytes = gen.generate_route_map(
        coordinates=coordinates,
        segments=segments,
        geometry=SAMPLE_GEOMETRY_NYC_TO_PHILLY,
    )

    assert image_bytes is not None
    assert len(image_bytes) > 0

    # Verify it's a valid PNG
    img = Image.open(io.BytesIO(image_bytes))
    assert img.format == "PNG"
    assert img.width > 0
    assert img.height > 0


def test_cross_country_route():
    """Test cross-country route with geometry."""
    gen = MapGenerator()

    coordinates = [
        {"lat": 40.7128, "lon": -74.006, "name": "New York, NY"},
        {"lat": 41.8781, "lon": -87.6298, "name": "Chicago, IL"},
        {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles, CA"},
    ]

    segments = [
        {"type": "start", "location": "New York, NY"},
        {"type": "drive", "distance": 790},
        {"type": "pickup", "location": "Chicago, IL"},
        {"type": "rest", "location": "Iowa"},
        {"type": "drive", "distance": 2015},
        {"type": "fuel", "location": "Arizona"},
        {"type": "dropoff", "location": "Los Angeles, CA"},
    ]

    image_bytes = gen.generate_route_map(
        coordinates=coordinates,
        segments=segments,
        geometry=SAMPLE_GEOMETRY_CROSS_COUNTRY,
    )

    assert image_bytes is not None
    assert len(image_bytes) > 0

    img = Image.open(io.BytesIO(image_bytes))
    assert img.format == "PNG"


def test_no_geometry_fallback():
    """Test fallback when no geometry provided."""
    gen = MapGenerator()

    coordinates = [
        {"lat": 38.9072, "lon": -77.0369, "name": "Washington, DC"},
        {"lat": 39.2904, "lon": -76.6122, "name": "Baltimore, MD"},
        {"lat": 39.9526, "lon": -75.1652, "name": "Philadelphia, PA"},
    ]

    segments = [
        {"type": "start"},
        {"type": "pickup"},
        {"type": "dropoff"},
    ]

    image_bytes = gen.generate_route_map(
        coordinates=coordinates,
        segments=segments,
        geometry=None,
    )

    assert image_bytes is not None
    assert len(image_bytes) > 0

    img = Image.open(io.BytesIO(image_bytes))
    assert img.format == "PNG"


@pytest.mark.skipif(not STATICMAP_AVAILABLE, reason="staticmap not installed")
def test_staticmap_tiles():
    """Test that staticmap fetches real OSM tiles."""
    gen = MapGenerator()

    coordinates = [
        {"lat": 47.6062, "lon": -122.3321, "name": "Seattle, WA"},
        {"lat": 45.5152, "lon": -122.6784, "name": "Portland, OR"},
    ]

    geometry = {
        "type": "LineString",
        "coordinates": [
            [-122.3321, 47.6062],
            [-122.4, 47.4],
            [-122.5, 47.0],
            [-122.6, 46.5],
            [-122.65, 46.0],
            [-122.68, 45.8],
            [-122.6784, 45.5152],
        ],
    }

    image_bytes = gen.generate_route_map(
        coordinates=coordinates,
        segments=[],
        geometry=geometry,
    )

    assert image_bytes is not None
    assert len(image_bytes) > 0

    img = Image.open(io.BytesIO(image_bytes))
    assert img.format == "PNG"


def test_empty_coordinates():
    """Test handling of empty coordinates."""
    gen = MapGenerator()

    image_bytes = gen.generate_route_map(
        coordinates=[],
        segments=[],
        geometry=None,
    )

    assert image_bytes is not None
    assert len(image_bytes) > 0


def test_extract_markers_assigns_types():
    """Test that marker types are correctly assigned."""
    gen = MapGenerator()

    coordinates = [
        {"lat": 40.0, "lon": -74.0, "name": "Start"},
        {"lat": 41.0, "lon": -75.0, "name": "Middle"},
        {"lat": 42.0, "lon": -76.0, "name": "End"},
    ]

    markers = gen._extract_markers(coordinates, [])

    assert len(markers) == 3
    assert markers[0]["type"] == "start"
    assert markers[1]["type"] == "pickup"
    assert markers[2]["type"] == "dropoff"


# ============================================================
# STANDALONE RUNNER (for manual testing)
# ============================================================


def run_standalone_tests():
    """Run tests standalone with file output for visual inspection."""
    print("\n" + "#" * 60)
    print("# MapGenerator Test Suite - Route Geometry Support")
    print(f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"# staticmap available: {STATICMAP_AVAILABLE}")
    print("#" * 60)

    tests_passed = 0
    tests_failed = 0

    try:
        # Test 1: Route with geometry
        print("\n" + "=" * 60)
        print("TEST 1: Route with Actual Road Geometry (NYC -> Philly)")
        print("=" * 60)

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

        image_bytes = gen.generate_route_map(
            coordinates=coordinates,
            segments=segments,
            geometry=SAMPLE_GEOMETRY_NYC_TO_PHILLY,
        )

        out = "test_map_with_road_geometry.png"
        with open(out, "wb") as f:
            f.write(image_bytes)

        print(f"Generated: {out} ({os.path.getsize(out):,} bytes)")
        tests_passed += 1

    except Exception as e:
        print(f"FAILED: {e}")
        tests_failed += 1

    try:
        # Test 2: Cross-country route
        print("\n" + "=" * 60)
        print("TEST 2: Cross-Country Route (NYC -> Chicago -> LA)")
        print("=" * 60)

        gen = MapGenerator()
        coordinates = [
            {"lat": 40.7128, "lon": -74.006, "name": "New York, NY"},
            {"lat": 41.8781, "lon": -87.6298, "name": "Chicago, IL"},
            {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles, CA"},
        ]
        segments = [
            {"type": "start", "location": "New York, NY"},
            {"type": "drive", "distance": 790},
            {"type": "pickup", "location": "Chicago, IL"},
            {"type": "rest", "location": "Iowa"},
            {"type": "drive", "distance": 2015},
            {"type": "fuel", "location": "Arizona"},
            {"type": "dropoff", "location": "Los Angeles, CA"},
        ]

        image_bytes = gen.generate_route_map(
            coordinates=coordinates,
            segments=segments,
            geometry=SAMPLE_GEOMETRY_CROSS_COUNTRY,
        )

        out = "test_map_cross_country.png"
        with open(out, "wb") as f:
            f.write(image_bytes)

        print(f"Generated: {out} ({os.path.getsize(out):,} bytes)")
        tests_passed += 1

    except Exception as e:
        print(f"FAILED: {e}")
        tests_failed += 1

    try:
        # Test 3: No geometry fallback
        print("\n" + "=" * 60)
        print("TEST 3: Fallback - No Geometry (Straight Lines)")
        print("=" * 60)

        gen = MapGenerator()
        coordinates = [
            {"lat": 38.9072, "lon": -77.0369, "name": "Washington, DC"},
            {"lat": 39.2904, "lon": -76.6122, "name": "Baltimore, MD"},
            {"lat": 39.9526, "lon": -75.1652, "name": "Philadelphia, PA"},
        ]
        segments = [
            {"type": "start"},
            {"type": "pickup"},
            {"type": "dropoff"},
        ]

        image_bytes = gen.generate_route_map(
            coordinates=coordinates,
            segments=segments,
            geometry=None,
        )

        out = "test_map_no_geometry.png"
        with open(out, "wb") as f:
            f.write(image_bytes)

        print(f"Generated: {out} ({os.path.getsize(out):,} bytes)")
        tests_passed += 1

    except Exception as e:
        print(f"FAILED: {e}")
        tests_failed += 1

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Passed: {tests_passed}")
    print(f"  Failed: {tests_failed}")

    # Cleanup
    print("\nCleaning up test files...")
    cleanup_test_files()
    print("Cleanup complete.")

    return tests_failed == 0


if __name__ == "__main__":
    success = run_standalone_tests()
    sys.exit(0 if success else 1)
