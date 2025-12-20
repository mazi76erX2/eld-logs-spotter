import io
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from ..services.map_generator import MapGenerator


@pytest.fixture
def sample_coordinates():
    return [
        {"lat": 32.7767, "lon": -96.7970, "name": "Dallas, TX"},
        {"lat": 29.7604, "lon": -95.3698, "name": "Houston, TX"},
        {"lat": 33.7490, "lon": -84.3880, "name": "Atlanta, GA"},
    ]


@pytest.fixture
def sample_segments():
    return [
        {"type": "start", "location": "Dallas, TX"},
        {"type": "pickup", "location": "Houston, TX"},
        {"type": "drive", "location": "En route"},
        {"type": "rest", "location": "Rest Area"},
        {"type": "fuel", "location": "Fuel Station"},
        {"type": "dropoff", "location": "Atlanta, GA"},
    ]


@pytest.fixture
def fake_map_image_bytes():
    img = Image.new("RGB", (1200, 800), "white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@patch("route_calculator.services.map_generator.requests.get")
def test_generate_route_map_success(
    mock_get, sample_coordinates, sample_segments, fake_map_image_bytes
):
    mock_get.return_value = Mock(
        status_code=200,
        content=fake_map_image_bytes,
    )
    mock_get.return_value.raise_for_status = lambda: None

    generator = MapGenerator()
    image_bytes = generator.generate_route_map(
        coordinates=sample_coordinates,
        segments=sample_segments,
    )

    img = Image.open(io.BytesIO(image_bytes))
    assert img.format == "PNG"


def test_extract_markers_assigns_types(sample_coordinates):
    generator = MapGenerator()
    markers = generator._extract_markers(sample_coordinates, [])

    assert markers[0]["type"] == "start"
    assert markers[1]["type"] == "pickup"
    assert markers[-1]["type"] == "dropoff"
