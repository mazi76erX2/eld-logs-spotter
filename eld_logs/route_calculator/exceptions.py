import logging
from typing import Any

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(
    exc: Exception, context: dict[str, Any]
) -> Response | None:
    """
    Custom exception handler for DRF that provides consistent error responses
    and logs exceptions.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Customize the response data
        custom_response_data = {
            "error": True,
            "status_code": response.status_code,
        }

        # Handle different response data formats
        if isinstance(response.data, dict):
            if "detail" in response.data:
                custom_response_data["message"] = str(response.data["detail"])
            else:
                custom_response_data["errors"] = response.data
        elif isinstance(response.data, list):
            custom_response_data["errors"] = response.data
        else:
            custom_response_data["message"] = str(response.data)

        response.data = custom_response_data

        # Log 5xx errors
        if response.status_code >= 500:
            logger.error(
                "Server error: %s - %s",
                response.status_code,
                exc,
                exc_info=True,
            )

    else:
        # Unhandled exception - log and return 500
        logger.exception("Unhandled exception: %s", exc)

        response = Response(
            {
                "error": True,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "An unexpected error occurred. Please try again later.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response


class TripCalculationError(Exception):
    """Base exception for trip calculation errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class GeocodingError(TripCalculationError):
    """Exception raised when geocoding fails."""

    pass


class RouteCalculationError(TripCalculationError):
    """Exception raised when route calculation fails."""

    pass


class MapGenerationError(TripCalculationError):
    """Exception raised when map generation fails."""

    pass


class HOSViolationError(TripCalculationError):
    """Exception raised when HOS rules are violated."""

    pass
