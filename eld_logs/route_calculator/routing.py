from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r"^ws/trips/(?P<trip_id>\d+)/progress/$",
        consumers.TripProgressConsumer.as_asgi(),
    ),
    re_path(
        r"^ws/trips/$",
        consumers.TripListConsumer.as_asgi(),
    ),
    re_path(r"^ws/test/$", consumers.TestConsumer.as_asgi()),
]
