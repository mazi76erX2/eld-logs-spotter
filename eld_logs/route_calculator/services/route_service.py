import logging
from typing import Any, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class RouteService:
    """Service for calculating routes using OpenRouteService API."""

    BASE_URL = "https://api.openrouteservice.org"

    def __init__(self) -> None:
        """Initialize RouteService with API key."""
        self.api_key = settings.OPENROUTESERVICE_API_KEY
        if not self.api_key:
            raise ValueError("OPENROUTESERVICE_API_KEY not configured in settings")

    def geocode_location(self, location: str) -> Optional[dict[str, float]]:
        """
        Convert location string to coordinates using OpenRouteService geocoding.

        Args:
            location: Location name (e.g., "Dallas, TX")

        Returns:
            dictionary with lon, lat, and name or None if not found
        """
        try:
            url = f"{self.BASE_URL}/geocode/search"
            params = {"api_key": self.api_key, "text": location, "size": 1}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            if not data.get("features"):
                logger.warning(f"No geocoding results for: {location}")
                return None

            coords = data["features"][0]["geometry"]["coordinates"]
            place_name = data["features"][0]["properties"].get("label", location)

            return {"lon": coords[0], "lat": coords[1], "name": place_name}
        except requests.exceptions.RequestException as e:
            logger.error(f"Geocoding request failed for '{location}': {e}")
            return None
        except (KeyError, IndexError) as e:
            logger.error(f"Geocoding response parsing failed for '{location}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected geocoding error for '{location}': {e}")
            return None

    def get_route(self, coordinates: list[list[float]]) -> Optional[dict[str, Any]]:
        """
        Get route between coordinates using OpenRouteService directions API.

        Args:
            coordinates: list of [lon, lat] pairs

        Returns:
            Route data in GeoJSON format or None if calculation fails
        """
        try:
            url = f"{self.BASE_URL}/v2/directions/driving-hgv/geojson"
            headers = {
                "Authorization": self.api_key,
                "Content-Type": "application/json",
            }
            payload = {
                "coordinates": coordinates,
                "preference": "recommended",
                "units": "mi",
            }

            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()

            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Route calculation request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected route calculation error: {e}")
            return None

    def get_route_legs(self, route: dict[str, Any]) -> list[dict[str, float]]:
        """
        Extract route legs from OpenRouteService response.

        Args:
            route: Route data from OpenRouteService

        Returns:
            list of route legs with distance (miles) and duration (hours)
        """
        legs: list[dict[str, float]] = []

        try:
            if "features" not in route or not route["features"]:
                logger.warning("No features in route response")
                return legs

            feature = route["features"][0]
            summary = feature.get("properties", {}).get("summary", {})

            # Distance is already in miles (we set units="mi" in the request)
            # Duration is always in seconds
            distance_miles = summary.get("distance", 0)  # Already in miles!
            duration_hours = summary.get("duration", 0) / 3600.0  # Seconds to hours

            legs.append(
                {
                    "distance": round(distance_miles, 2),
                    "duration": round(duration_hours, 2),
                }
            )

            logger.info(
                f"Extracted route leg: {distance_miles:.2f} miles, "
                f"{duration_hours:.2f} hours"
            )

        except (KeyError, TypeError) as e:
            logger.error(f"Error extracting route legs: {e}")

        return legs
