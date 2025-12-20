from unittest.mock import patch

import pytest

from ..services.route_service import RouteService


@pytest.mark.django_db
@patch("route_calculator.services.route_service.requests.get")
def test_geocode_location_success(mock_get, settings):
    settings.OPENROUTESERVICE_API_KEY = "fake-key"

    mock_get.return_value.json.return_value = {
        "features": [
            {
                "geometry": {"coordinates": [-96.8, 32.7]},
                "properties": {"label": "Dallas, TX"},
            }
        ]
    }
    mock_get.return_value.raise_for_status = lambda: None

    service = RouteService()
    result = service.geocode_location("Dallas, TX")

    assert result["lat"] == 32.7
    assert result["lon"] == -96.8
