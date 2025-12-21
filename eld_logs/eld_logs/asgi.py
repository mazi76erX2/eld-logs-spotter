"""
ASGI config for eld_logs project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from decouple import config
from django.core.asgi import get_asgi_application

DJANGO_SETTINGS_MODULE: str = config(
    "DJANGO_SETTINGS_MODULE",
    default="eld_logs.settings.local",
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", DJANGO_SETTINGS_MODULE)

# Initialize Django ASGI application early to ensure settings are loaded
django_asgi_app = get_asgi_application()

from django.conf import settings
from route_calculator.routing import websocket_urlpatterns


# Use origin validator only in production
if settings.DEBUG:
    # In development, allow all WebSocket connections
    websocket_application = AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
else:
    # In production, validate origins
    from channels.security.websocket import AllowedHostsOriginValidator

    websocket_application = AllowedHostsOriginValidator(
        AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
    )

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": websocket_application,
    }
)
