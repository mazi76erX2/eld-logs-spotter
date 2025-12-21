from decouple import Csv, config

from .base import *

ALLOWED_HOSTS: list[str] = config(
    "ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv()
)

# define which origins are allowed
CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]

DEBUG = True

# Local file storage
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Disable security for local development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

INTERNAL_IPS = [
    # ...
    "127.0.0.1",
    # ...
]
