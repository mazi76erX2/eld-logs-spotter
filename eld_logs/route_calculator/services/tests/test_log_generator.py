import io

import pytest
from PIL import Image

from ..services.log_generator import LogGenerator


@pytest.fixture
def sample_log_data():
    return {
        "date": "04/09/2021",
        "total_miles": 350,
        "events": [
            {"start": 0, "end": 6, "status": "offDuty"},
            {"start": 6, "end": 8, "status": "driving"},
            {"start": 8, "end": 9, "status": "onDuty"},
            {"start": 9, "end": 24, "status": "offDuty"},
        ],
        "remarks": [{"location": "Richmond, VA"}],
    }


@pytest.fixture
def full_log_data():
    """Log data with all fields populated."""
    return {
        "date": "04/09/2021",
        "total_miles": 350,
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


def test_generate_log_image_returns_png(sample_log_data):
    """Test that basic log generation returns a valid PNG image."""
    generator = LogGenerator()

    image_bytes = generator.generate_log_image(
        log_data=sample_log_data,
        day_number=1,
        driver_name="John Doe",
        carrier_name="Test Carrier",
        main_office="Washington, D.C.",
        co_driver="",
        from_address="",
        to_address="",
        home_terminal_address="",
        truck_number="",
        shipping_doc="",
    )

    assert isinstance(image_bytes, (bytes, bytearray))
    img = Image.open(io.BytesIO(image_bytes))
    assert img.format == "PNG"


def test_generate_log_image_with_all_parameters(full_log_data):
    """Test log generation with all parameters populated."""
    generator = LogGenerator()

    image_bytes = generator.generate_log_image(
        log_data=full_log_data,
        day_number=1,
        driver_name="John E. Doe",
        carrier_name="John Doe's Transportation",
        main_office="Washington, D.C.",
        co_driver="Jane Doe",
        from_address="Richmond, VA",
        to_address="Newark, NJ",
        home_terminal_address="Washington, D.C.",
        truck_number="123, 20544",
        shipping_doc="101601",
    )

    assert isinstance(image_bytes, (bytes, bytearray))
    img = Image.open(io.BytesIO(image_bytes))
    assert img.format == "PNG"


def test_generate_log_image_with_default_parameters(sample_log_data):
    """Test log generation using default parameter values."""
    generator = LogGenerator()

    image_bytes = generator.generate_log_image(
        log_data=sample_log_data,
        day_number=1,
        driver_name="John Doe",
        carrier_name="Test Carrier",
    )

    assert isinstance(image_bytes, (bytes, bytearray))
    img = Image.open(io.BytesIO(image_bytes))
    assert img.format == "PNG"


def test_generate_log_image_with_fallback_to_log_data():
    """Test that log_data values are used as fallback when parameters are empty."""
    generator = LogGenerator()

    log_data = {
        "date": "04/09/2021",
        "total_miles": 500,
        "from_address": "Atlanta, GA",
        "to_address": "Miami, FL",
        "home_terminal_address": "Atlanta, GA",
        "truck_number": "TRUCK-999",
        "shipping_doc": "SHIP-12345",
        "events": [
            {"start": 0, "end": 8, "status": "offDuty"},
            {"start": 8, "end": 16, "status": "driving"},
            {"start": 16, "end": 24, "status": "offDuty"},
        ],
        "remarks": [],
    }

    image_bytes = generator.generate_log_image(
        log_data=log_data,
        day_number=1,
        driver_name="Test Driver",
        carrier_name="Test Carrier",
        main_office="Atlanta, GA",
        co_driver="",
        from_address="",  # Should fallback to log_data
        to_address="",  # Should fallback to log_data
        home_terminal_address="",  # Should fallback to log_data
        truck_number="",  # Should fallback to log_data
        shipping_doc="",  # Should fallback to log_data
    )

    assert isinstance(image_bytes, (bytes, bytearray))
    img = Image.open(io.BytesIO(image_bytes))
    assert img.format == "PNG"


def test_generate_log_image_with_empty_events():
    """Test log generation with no events."""
    generator = LogGenerator()

    log_data = {
        "date": "04/09/2021",
        "total_miles": 0,
        "events": [],
        "remarks": [],
    }

    image_bytes = generator.generate_log_image(
        log_data=log_data,
        day_number=1,
        driver_name="John Doe",
        carrier_name="Test Carrier",
        main_office="Washington, D.C.",
    )

    assert isinstance(image_bytes, (bytes, bytearray))
    img = Image.open(io.BytesIO(image_bytes))
    assert img.format == "PNG"


def test_generate_log_image_with_multiple_remarks(full_log_data):
    """Test log generation with multiple remarks."""
    generator = LogGenerator()

    image_bytes = generator.generate_log_image(
        log_data=full_log_data,
        day_number=1,
        driver_name="John Doe",
        carrier_name="Test Carrier",
        main_office="Washington, D.C.",
        from_address="Richmond, VA",
        to_address="Newark, NJ",
    )

    assert isinstance(image_bytes, (bytes, bytearray))
    img = Image.open(io.BytesIO(image_bytes))
    assert img.format == "PNG"


def test_generate_log_image_with_empty_remarks():
    """Test log generation with empty remarks list."""
    generator = LogGenerator()

    log_data = {
        "date": "04/09/2021",
        "total_miles": 200,
        "events": [
            {"start": 0, "end": 12, "status": "offDuty"},
            {"start": 12, "end": 20, "status": "driving"},
            {"start": 20, "end": 24, "status": "offDuty"},
        ],
        "remarks": [],
    }

    image_bytes = generator.generate_log_image(
        log_data=log_data,
        day_number=1,
        driver_name="John Doe",
        carrier_name="Test Carrier",
    )

    assert isinstance(image_bytes, (bytes, bytearray))
    img = Image.open(io.BytesIO(image_bytes))
    assert img.format == "PNG"


def test_generate_log_image_with_remarks_missing_location():
    """Test log generation with remarks that have no location."""
    generator = LogGenerator()

    log_data = {
        "date": "04/09/2021",
        "total_miles": 200,
        "events": [
            {"start": 0, "end": 12, "status": "offDuty"},
            {"start": 12, "end": 20, "status": "driving"},
            {"start": 20, "end": 24, "status": "offDuty"},
        ],
        "remarks": [
            {"location": "Richmond, VA"},
            {},  # Missing location
            {"location": ""},  # Empty location
            {"location": "Baltimore, MD"},
        ],
    }

    image_bytes = generator.generate_log_image(
        log_data=log_data,
        day_number=1,
        driver_name="John Doe",
        carrier_name="Test Carrier",
    )

    assert isinstance(image_bytes, (bytes, bytearray))
    img = Image.open(io.BytesIO(image_bytes))
    assert img.format == "PNG"


def test_generate_log_image_with_all_duty_statuses():
    """Test log generation with all four duty statuses."""
    generator = LogGenerator()

    log_data = {
        "date": "04/09/2021",
        "total_miles": 300,
        "events": [
            {"start": 0, "end": 6, "status": "offDuty"},
            {"start": 6, "end": 8, "status": "sleeper"},
            {"start": 8, "end": 16, "status": "driving"},
            {"start": 16, "end": 18, "status": "onDuty"},
            {"start": 18, "end": 24, "status": "offDuty"},
        ],
        "remarks": [{"location": "Test Location"}],
    }

    image_bytes = generator.generate_log_image(
        log_data=log_data,
        day_number=1,
        driver_name="John Doe",
        carrier_name="Test Carrier",
        main_office="Washington, D.C.",
        truck_number="T-1234",
        shipping_doc="DOC-5678",
    )

    assert isinstance(image_bytes, (bytes, bytearray))
    img = Image.open(io.BytesIO(image_bytes))
    assert img.format == "PNG"


def test_generate_log_image_with_fractional_hours():
    """Test log generation with fractional hour values."""
    generator = LogGenerator()

    log_data = {
        "date": "04/09/2021",
        "total_miles": 275,
        "events": [
            {"start": 0, "end": 6.5, "status": "offDuty"},
            {"start": 6.5, "end": 7.25, "status": "onDuty"},
            {"start": 7.25, "end": 11.75, "status": "driving"},
            {"start": 11.75, "end": 12.5, "status": "offDuty"},
            {"start": 12.5, "end": 17.33, "status": "driving"},
            {"start": 17.33, "end": 24, "status": "offDuty"},
        ],
        "remarks": [],
    }

    image_bytes = generator.generate_log_image(
        log_data=log_data,
        day_number=2,
        driver_name="Jane Smith",
        carrier_name="Smith Trucking",
    )

    assert isinstance(image_bytes, (bytes, bytearray))
    img = Image.open(io.BytesIO(image_bytes))
    assert img.format == "PNG"


def test_generate_log_image_with_co_driver():
    """Test log generation with co-driver specified."""
    generator = LogGenerator()

    log_data = {
        "date": "04/09/2021",
        "total_miles": 600,
        "events": [
            {"start": 0, "end": 10, "status": "sleeper"},
            {"start": 10, "end": 20, "status": "driving"},
            {"start": 20, "end": 24, "status": "sleeper"},
        ],
        "remarks": [{"location": "Truck Stop, OH"}],
    }

    image_bytes = generator.generate_log_image(
        log_data=log_data,
        day_number=1,
        driver_name="John Doe",
        carrier_name="Team Trucking Inc.",
        main_office="Columbus, OH",
        co_driver="Jane Doe",
        from_address="New York, NY",
        to_address="Los Angeles, CA",
        home_terminal_address="Columbus, OH",
        truck_number="TEAM-001",
        shipping_doc="TEAM-SHIP-999",
    )

    assert isinstance(image_bytes, (bytes, bytearray))
    img = Image.open(io.BytesIO(image_bytes))
    assert img.format == "PNG"


def test_generate_log_image_invalid_status_ignored():
    """Test that invalid duty statuses are ignored."""
    generator = LogGenerator()

    log_data = {
        "date": "04/09/2021",
        "total_miles": 100,
        "events": [
            {"start": 0, "end": 8, "status": "offDuty"},
            {"start": 8, "end": 12, "status": "invalidStatus"},  # Invalid
            {"start": 12, "end": 16, "status": "driving"},
            {"start": 16, "end": 24, "status": "offDuty"},
        ],
        "remarks": [],
    }

    image_bytes = generator.generate_log_image(
        log_data=log_data,
        day_number=1,
        driver_name="John Doe",
        carrier_name="Test Carrier",
    )

    assert isinstance(image_bytes, (bytes, bytearray))
    img = Image.open(io.BytesIO(image_bytes))
    assert img.format == "PNG"


def test_generate_log_image_boundary_hours():
    """Test log generation with events at boundary hours (0 and 24)."""
    generator = LogGenerator()

    log_data = {
        "date": "04/09/2021",
        "total_miles": 400,
        "events": [
            {"start": 0, "end": 24, "status": "driving"},
        ],
        "remarks": [],
    }

    image_bytes = generator.generate_log_image(
        log_data=log_data,
        day_number=1,
        driver_name="Marathon Driver",
        carrier_name="Test Carrier",
    )

    assert isinstance(image_bytes, (bytes, bytearray))
    img = Image.open(io.BytesIO(image_bytes))
    assert img.format == "PNG"


def test_log_generator_initialization():
    """Test that LogGenerator initializes correctly."""
    generator = LogGenerator()

    assert generator.fonts is not None
    assert "small" in generator.fonts
    assert "medium" in generator.fonts
    assert "x-small" in generator.fonts
