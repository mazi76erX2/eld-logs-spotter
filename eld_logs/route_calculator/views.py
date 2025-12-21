import logging
from typing import Any

from django.http import FileResponse, HttpResponse
from drf_spectacular.utils import (OpenApiParameter, OpenApiResponse,
                                   extend_schema, extend_schema_view)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response

from .models import TripCalculation
from .serializers import (MapStatusSerializer, TripCalculationSerializer,
                          TripInputSerializer, TripStatusSerializer)
from .services.log_generator import LogGenerator
from .tasks import calculate_trip_task, generate_map_task

logger = logging.getLogger(__name__)


class TripPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"  # This enables ?page_size=2
    max_page_size = 100


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
)
class TripCalculationViewSet(viewsets.ModelViewSet):
    """
    API endpoints for trip route calculation, FMCSA HOS logs,
    ELD daily logs, and route map visualization.
    """

    queryset = TripCalculation.objects.all()
    serializer_class = TripCalculationSerializer
    pagination_class = TripPagination

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
            "- Route map generation (async)\n\n"
            "Returns immediately with a processing status.\n"
            "Connect to WebSocket at `/ws/trips/{id}/progress/` for real-time updates."
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
                        "websocket_url": {"type": "string"},
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

        # Build WebSocket URL
        ws_scheme = "wss" if request.is_secure() else "ws"
        ws_url = f"{ws_scheme}://{request.get_host()}/ws/trips/{trip.id}/progress/"

        return Response(
            {
                "id": trip.id,
                "status": "processing",
                "message": "Trip calculation started. Connect to WebSocket for real-time updates.",
                "websocket_url": ws_url,
                "polling_url": f"/api/trips/{trip.id}/status/",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    # =========================================================================
    # Get Status (Enhanced for polling fallback)
    # =========================================================================
    @extend_schema(
        tags=["Trips"],
        summary="Get trip and map status",
        description=(
            "Get the current processing status of trip calculation and map generation.\n"
            "Use this endpoint for polling if WebSocket is not available."
        ),
        responses={
            200: TripStatusSerializer,
            404: OpenApiResponse(description="Trip not found"),
        },
    )
    @action(detail=True, methods=["get"], url_path="status")
    def get_status(self, request: Request, pk: Any = None) -> Response:
        """Get comprehensive trip and map status."""
        trip = self.get_object()
        return Response(
            {
                "id": trip.id,
                "status": trip.status,
                "progress": trip.progress,
                "error_message": trip.error_message,
                "map_status": trip.map_status,
                "map_progress": trip.map_progress,
                "map_error_message": trip.map_error_message,
                "overall_progress": trip.overall_progress,
                "is_completed": trip.is_completed,
                "is_map_ready": trip.is_map_ready,
                "total_distance": trip.total_distance,
                "total_driving_time": trip.total_driving_time,
                "map_url": trip.map_file.url if trip.map_file else None,
            }
        )

    # =========================================================================
    # Retry Map Generation
    # =========================================================================
    @extend_schema(
        tags=["Maps"],
        summary="Retry map generation",
        description="Retry failed map generation for a completed trip.",
        responses={
            202: OpenApiResponse(description="Map generation restarted"),
            400: OpenApiResponse(description="Trip not ready for map generation"),
            404: OpenApiResponse(description="Trip not found"),
        },
    )
    @action(detail=True, methods=["post"], url_path="retry-map")
    def retry_map(self, request: Request, pk: Any = None) -> Response:
        """Retry failed map generation."""
        trip = self.get_object()

        if trip.status != TripCalculation.JobStatus.COMPLETED:
            return Response(
                {"error": "Trip calculation must be completed before generating map"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if trip.map_status == TripCalculation.MapStatus.GENERATING:
            return Response(
                {"error": "Map generation already in progress"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Reset map status and trigger new generation
        trip.map_status = TripCalculation.MapStatus.GENERATING
        trip.map_progress = 0
        trip.map_error_message = None
        trip.save(
            update_fields=[
                "map_status",
                "map_progress",
                "map_error_message",
                "updated_at",
            ]
        )

        task = generate_map_task.delay(trip.id)
        trip.map_task_id = task.id
        trip.save(update_fields=["map_task_id", "updated_at"])

        return Response(
            {
                "id": trip.id,
                "message": "Map generation restarted",
                "map_task_id": task.id,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    # =========================================================================
    # Download Route Map (Updated to serve from file or generate)
    # =========================================================================
    @extend_schema(
        tags=["Maps"],
        summary="Download route map",
        description=(
            "Download a PNG map visualizing the trip route.\n\n"
            "If the map has been pre-generated, it's served from storage.\n"
            "Returns 202 if map is still generating."
        ),
        responses={
            200: OpenApiResponse(
                description="PNG image",
                response={"image/png": {"type": "string", "format": "binary"}},
            ),
            202: OpenApiResponse(description="Map is still generating"),
            404: OpenApiResponse(description="Route data not available"),
        },
    )
    @action(detail=True, methods=["get"], url_path="download-map")
    def download_map(self, request: Request, pk: Any = None) -> HttpResponse:
        """Download route map image."""
        try:
            trip = self.get_object()

            # Check if map is ready
            if trip.is_map_ready and trip.map_url:
                # Redirect to the map URL (Cloudinary or local)
                from django.shortcuts import redirect
                return redirect(trip.map_url)

            # Check if map is generating
            if trip.map_status == TripCalculation.MapStatus.GENERATING:
                return Response(
                    {
                        "status": "generating",
                        "progress": trip.map_progress,
                        "message": "Map is still being generated. Please try again later.",
                    },
                    status=status.HTTP_202_ACCEPTED,
                )

            # Check if map generation failed
            if trip.map_status == TripCalculation.MapStatus.FAILED:
                return Response(
                    {
                        "status": "failed",
                        "error": trip.map_error_message or "Map generation failed",
                        "retry_url": f"/api/trips/{trip.id}/retry-map/",
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Map hasn't been generated yet - trigger generation if trip is complete
            if trip.is_completed:
                task = generate_map_task.delay(trip.id)
                trip.map_task_id = task.id
                trip.map_status = TripCalculation.MapStatus.GENERATING
                trip.save(update_fields=["map_task_id", "map_status", "updated_at"])

                return Response(
                    {
                        "status": "generating",
                        "progress": 0,
                        "message": "Map generation started. Please try again in a few moments.",
                    },
                    status=status.HTTP_202_ACCEPTED,
                )

            return Response(
                {"error": "Trip calculation not yet complete"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as e:
            logger.error("Error serving route map: %s", e, exc_info=True)
            return Response(
                {"error": "Error serving route map"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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

            required_fields = ["events", "date", "total_miles"]
            missing = [f for f in required_fields if f not in log_data]
            if missing:
                return Response(
                    {"error": f"Log data missing required fields: {missing}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            generator = LogGenerator()
            image_bytes = generator.generate_log_image(
                log_data=log_data,
                day_number=day,
                driver_name=log_data.get("driver_name", "Driver Name"),
                carrier_name=log_data.get("carrier_name", "Carrier Name"),
                main_office=log_data.get("main_office", "Washington, D.C."),
                co_driver=log_data.get("co_driver", ""),
                from_address=log_data.get("from_address", ""),
                to_address=log_data.get("to_address", ""),
                home_terminal_address=log_data.get("home_terminal_address", ""),
                truck_number=log_data.get("truck_number", ""),
                shipping_doc=log_data.get("shipping_doc", ""),
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
    # Get Trip Summary
    # =========================================================================
    @extend_schema(
        tags=["Trips"],
        summary="Get trip summary",
        description="Get a summary of the trip including distances and times.",
        responses={200: OpenApiResponse(description="Trip summary")},
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
                "map_status": trip.map_status,
                "is_map_ready": trip.is_map_ready,
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
        responses={200: OpenApiResponse(description="List of daily logs")},
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
