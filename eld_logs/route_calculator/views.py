import logging
from typing import Any

from django.http import HttpResponse
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from .models import TripCalculation
from .serializers import TripCalculationSerializer, TripInputSerializer
from .services.log_generator import LogGenerator
from .services.map_generator import MapGenerator
from .tasks import calculate_trip_task

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        tags=["Trips"],
        summary="List trip calculations",
        description="Retrieve a paginated list of trip calculations.",
        responses={200: TripCalculationSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Trips"],
        summary="Retrieve a trip calculation",
        description="Retrieve a single trip calculation by ID.",
        responses={200: TripCalculationSerializer},
    ),
    create=extend_schema(
        tags=["Trips"],
        summary="Create trip calculation (unused)",
        description="Trip calculations are created via the calculate endpoint.",
        exclude=True,
    ),
)
class TripCalculationViewSet(viewsets.ModelViewSet):
    """
    API endpoints for trip route calculation, FMCSA HOS logs,
    ELD daily logs, and route map visualization.
    """

    queryset = TripCalculation.objects.all()
    serializer_class = TripCalculationSerializer

    def get_queryset(self):
        """Return trips ordered by most recent."""
        return TripCalculation.objects.all().order_by("-created_at")

    # =========================================================================
    # Calculate Trip
    # =========================================================================
    @extend_schema(
        tags=["Trips"],
        summary="Calculate route and generate logs",
        description=(
            "Starts an asynchronous trip calculation including:\n"
            "- Route calculation (OpenRouteService)\n"
            "- FMCSA HOS compliance\n"
            "- ELD daily logs\n"
            "- Route map generation\n\n"
            "Returns immediately with a processing status."
        ),
        request=TripInputSerializer,
        responses={
            202: OpenApiResponse(
                description="Trip calculation started",
                response={
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "status": {"type": "string"},
                        "message": {"type": "string"},
                    },
                },
            ),
            400: OpenApiResponse(description="Invalid input"),
        },
    )
    @action(detail=False, methods=["post"], url_path="calculate")
    def calculate(self, request: Request) -> Response:
        """Start async trip calculation."""
        serializer = TripInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        trip = TripCalculation.objects.create(
            current_location=serializer.validated_data["current_location"],
            pickup_location=serializer.validated_data["pickup_location"],
            dropoff_location=serializer.validated_data["dropoff_location"],
            current_cycle_used=serializer.validated_data["current_cycle_used"],
            status=TripCalculation.JobStatus.PENDING,
        )

        calculate_trip_task.delay(trip.id)

        logger.info("Trip calculation initiated: %s", trip.id)

        return Response(
            {
                "id": trip.id,
                "status": "processing",
                "message": "Trip calculation started. Use the result endpoint to check status.",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    # =========================================================================
    # Get Result
    # =========================================================================
    @extend_schema(
        tags=["Trips"],
        summary="Get calculation result",
        description="Retrieve the full calculation result including route, logs, and totals.",
        responses={
            200: TripCalculationSerializer,
            404: OpenApiResponse(description="Trip not found"),
        },
    )
    @action(detail=True, methods=["get"], url_path="result")
    def result(self, request: Request, pk: Any = None) -> Response:
        """Get calculation result."""
        trip = self.get_object()
        serializer = self.get_serializer(trip)
        return Response(serializer.data)

    # =========================================================================
    # Download Daily Log
    # =========================================================================
    @extend_schema(
        tags=["Logs"],
        summary="Download ELD daily log image",
        description="Download a PNG image of the FMCSA-compliant ELD daily log.",
        parameters=[
            OpenApiParameter(
                name="day",
                description="Day number of the trip (1-based)",
                required=False,
                type=int,
            )
        ],
        responses={
            200: OpenApiResponse(
                description="PNG image",
                response={"image/png": {"type": "string", "format": "binary"}},
            ),
            404: OpenApiResponse(description="Log not found"),
            400: OpenApiResponse(description="Invalid log data"),
        },
    )
    @action(detail=True, methods=["get"], url_path="download-log")
    def download_log(self, request: Request, pk: Any = None) -> HttpResponse:
        """Download ELD log image."""
        try:
            trip = self.get_object()
            day = int(request.query_params.get("day", 1))

            if not trip.logs_data or day < 1 or day > len(trip.logs_data):
                return Response(
                    {"error": f"Log for day {day} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            log_data = trip.logs_data[day - 1]

            # Validate required fields
            required_fields = ["events", "date", "total_miles"]
            missing = [f for f in required_fields if f not in log_data]
            if missing:
                return Response(
                    {"error": f"Log data missing required fields: {missing}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Extract all log fields with defaults from log_data
            driver_name = log_data.get("driver_name", "Driver Name")
            carrier_name = log_data.get("carrier_name", "Carrier Name")
            main_office = log_data.get("main_office", "Washington, D.C.")
            co_driver = log_data.get("co_driver", "")
            from_address = log_data.get("from_address", "")
            to_address = log_data.get("to_address", "")
            home_terminal_address = log_data.get("home_terminal_address", main_office)
            truck_number = log_data.get("truck_number", "")
            shipping_doc = log_data.get("shipping_doc", "")

            generator = LogGenerator()
            image_bytes = generator.generate_log_image(
                log_data=log_data,
                day_number=day,
                driver_name=driver_name,
                carrier_name=carrier_name,
                main_office=main_office,
                co_driver=co_driver,
                from_address=from_address,
                to_address=to_address,
                home_terminal_address=home_terminal_address,
                truck_number=truck_number,
                shipping_doc=shipping_doc,
            )

            response = HttpResponse(image_bytes, content_type="image/png")
            response["Content-Disposition"] = (
                f'attachment; filename="eld_log_trip_{trip.id}_day_{day}.png"'
            )

            logger.info("Log downloaded: Trip %s, Day %s", trip.id, day)
            return response

        except ValueError:
            return Response(
                {"error": "Invalid day parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error("Error generating log image: %s", e, exc_info=True)
            return Response(
                {"error": "Error generating log image"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # =========================================================================
    # Download Route Map
    # =========================================================================
    @extend_schema(
        tags=["Maps"],
        summary="Download route map",
        description=(
            "Download a PNG map visualizing the trip route following actual roads. "
            "The route geometry comes from OpenRouteService and shows the real path "
            "the driver will take, not just straight lines between waypoints."
        ),
        responses={
            200: OpenApiResponse(
                description="PNG image",
                response={"image/png": {"type": "string", "format": "binary"}},
            ),
            404: OpenApiResponse(description="Route data not available"),
            400: OpenApiResponse(description="Invalid coordinates"),
        },
    )
    @action(detail=True, methods=["get"], url_path="download-map")
    def download_map(self, request: Request, pk: Any = None) -> HttpResponse:
        """Download route map image with actual road geometry."""
        try:
            trip = self.get_object()

            # Check if coordinates are available
            if not trip.coordinates:
                return Response(
                    {"error": "Coordinates not available for this trip"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Extract and validate coordinates
            current_coord = trip.coordinates.get("current", {})
            pickup_coord = trip.coordinates.get("pickup", {})
            dropoff_coord = trip.coordinates.get("dropoff", {})

            # Validate each coordinate has required fields
            for coord, name in [
                (current_coord, "current"),
                (pickup_coord, "pickup"),
                (dropoff_coord, "dropoff"),
            ]:
                if "lat" not in coord or "lon" not in coord:
                    return Response(
                        {"error": f"Invalid {name} coordinates"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Build coordinates list for map generator
            coordinates = [
                {
                    "lat": current_coord["lat"],
                    "lon": current_coord["lon"],
                    "name": current_coord.get("name", "Start"),
                },
                {
                    "lat": pickup_coord["lat"],
                    "lon": pickup_coord["lon"],
                    "name": pickup_coord.get("name", "Pickup"),
                },
                {
                    "lat": dropoff_coord["lat"],
                    "lon": dropoff_coord["lon"],
                    "name": dropoff_coord.get("name", "Dropoff"),
                },
            ]

            # Get segments and geometry from route_data
            segments = []
            geometry = None

            if trip.route_data:
                segments = trip.route_data.get("segments", [])
                # This is the actual road geometry from OpenRouteService!
                # It contains the polyline that follows real roads
                geometry = trip.route_data.get("geometry")

            # Generate map with actual route geometry
            generator = MapGenerator()
            image_bytes = generator.generate_route_map(
                coordinates=coordinates,
                segments=segments,
                geometry=geometry,  # Pass the ORS geometry for road-following route
            )

            response = HttpResponse(image_bytes, content_type="image/png")
            response["Content-Disposition"] = (
                f'attachment; filename="route_map_trip_{trip.id}.png"'
            )

            logger.info(
                "Route map downloaded: Trip %s (geometry: %s)",
                trip.id,
                "yes" if geometry else "no",
            )
            return response

        except Exception as e:
            logger.error("Error generating route map: %s", e, exc_info=True)
            return Response(
                {"error": "Error generating route map"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # =========================================================================
    # Get Trip Status
    # =========================================================================
    @extend_schema(
        tags=["Trips"],
        summary="Get trip status",
        description="Get the current processing status of a trip calculation.",
        responses={
            200: OpenApiResponse(
                description="Trip status",
                response={
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "status": {"type": "string"},
                        "error_message": {"type": "string", "nullable": True},
                    },
                },
            ),
            404: OpenApiResponse(description="Trip not found"),
        },
    )
    @action(detail=True, methods=["get"], url_path="status")
    def get_status(self, request: Request, pk: Any = None) -> Response:
        """Get trip calculation status."""
        trip = self.get_object()
        return Response(
            {
                "id": trip.id,
                "status": trip.status,
                "error_message": trip.error_message,
            }
        )

    # =========================================================================
    # Get Trip Summary
    # =========================================================================
    @extend_schema(
        tags=["Trips"],
        summary="Get trip summary",
        description="Get a summary of the trip including distances and times.",
        responses={
            200: OpenApiResponse(
                description="Trip summary",
                response={
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "status": {"type": "string"},
                        "current_location": {"type": "string"},
                        "pickup_location": {"type": "string"},
                        "dropoff_location": {"type": "string"},
                        "total_distance": {"type": "number", "nullable": True},
                        "total_driving_time": {"type": "number", "nullable": True},
                        "total_trip_time": {"type": "number", "nullable": True},
                        "num_days": {"type": "integer"},
                        "created_at": {"type": "string", "format": "date-time"},
                    },
                },
            ),
            404: OpenApiResponse(description="Trip not found"),
        },
    )
    @action(detail=True, methods=["get"], url_path="summary")
    def summary(self, request: Request, pk: Any = None) -> Response:
        """Get trip summary."""
        trip = self.get_object()

        num_days = len(trip.logs_data) if trip.logs_data else 0

        return Response(
            {
                "id": trip.id,
                "status": trip.status,
                "current_location": trip.current_location,
                "pickup_location": trip.pickup_location,
                "dropoff_location": trip.dropoff_location,
                "total_distance": trip.total_distance,
                "total_driving_time": trip.total_driving_time,
                "total_trip_time": trip.total_trip_time,
                "num_days": num_days,
                "created_at": trip.created_at.isoformat(),
            }
        )

    # =========================================================================
    # List Daily Logs
    # =========================================================================
    @extend_schema(
        tags=["Logs"],
        summary="List daily logs",
        description="Get a list of all daily logs for a trip with basic info.",
        responses={
            200: OpenApiResponse(
                description="List of daily logs",
                response={
                    "type": "object",
                    "properties": {
                        "trip_id": {"type": "integer"},
                        "total_days": {"type": "integer"},
                        "logs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "day": {"type": "integer"},
                                    "date": {"type": "string"},
                                    "total_miles": {"type": "number"},
                                    "download_url": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            ),
            404: OpenApiResponse(description="Trip not found or no logs available"),
        },
    )
    @action(detail=True, methods=["get"], url_path="logs")
    def list_logs(self, request: Request, pk: Any = None) -> Response:
        """List all daily logs for a trip."""
        trip = self.get_object()

        if not trip.logs_data:
            return Response(
                {"error": "No logs available for this trip"},
                status=status.HTTP_404_NOT_FOUND,
            )

        logs_info = []
        for i, log in enumerate(trip.logs_data, start=1):
            logs_info.append(
                {
                    "day": i,
                    "date": log.get("date", ""),
                    "total_miles": log.get("total_miles", 0),
                    "from_address": log.get("from_address", ""),
                    "to_address": log.get("to_address", ""),
                    "download_url": f"/api/trips/{trip.id}/download-log/?day={i}",
                }
            )

        return Response(
            {
                "trip_id": trip.id,
                "total_days": len(trip.logs_data),
                "logs": logs_info,
            }
        )
