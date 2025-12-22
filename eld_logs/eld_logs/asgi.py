import os
import logging

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from decouple import config
from django.core.asgi import get_asgi_application

logger = logging.getLogger(__name__)

DJANGO_SETTINGS_MODULE: str = config(
    "DJANGO_SETTINGS_MODULE",
    default="eld_logs.settings.local",
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", DJANGO_SETTINGS_MODULE)

# Initialize Django ASGI application early to ensure settings are loaded
django_asgi_app = get_asgi_application()

from django.conf import settings
from route_calculator.routing import websocket_urlpatterns


class OriginValidatorWithLogging:
    """Custom origin validator with logging for debugging."""

    def __init__(self, application, allowed_origins=None):
        self.application = application
        self.allowed_origins = allowed_origins or []

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            origin = None
            for header_name, header_value in scope.get("headers", []):
                if header_name == b"origin":
                    origin = header_value.decode("utf-8")
                    break

            logger.info(f"WebSocket connection attempt - Origin: {origin}")
            logger.info(f"Allowed hosts: {settings.ALLOWED_HOSTS}")

            # Check origin
            if origin:
                from urllib.parse import urlparse

                parsed = urlparse(origin)
                origin_host = parsed.netloc

                # Check against allowed hosts
                allowed = False
                for host in settings.ALLOWED_HOSTS:
                    if host == "*":
                        allowed = True
                        break
                    elif host.startswith("."):
                        # Wildcard subdomain
                        if origin_host.endswith(host) or origin_host == host[1:]:
                            allowed = True
                            break
                    elif origin_host == host:
                        allowed = True
                        break

                if not allowed:
                    logger.warning(
                        f"WebSocket origin rejected: {origin} (host: {origin_host})"
                    )
                    # Close with 403
                    await send({"type": "websocket.close", "code": 4003})
                    return

                logger.info(f"WebSocket origin accepted: {origin}")

        return await self.application(scope, receive, send)


# Build WebSocket application
websocket_app = AuthMiddlewareStack(URLRouter(websocket_urlpatterns))

if settings.DEBUG:
    # In development, allow all WebSocket connections
    websocket_application = websocket_app
else:
    # In production, use our custom validator with logging
    websocket_application = OriginValidatorWithLogging(websocket_app)

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": websocket_application,
    }
)
