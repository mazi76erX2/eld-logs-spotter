from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path(
        "ws/trips/<int:trip_id>/progress/",
        consumers.TripProgressConsumer.as_asgi(),
    ),
]
