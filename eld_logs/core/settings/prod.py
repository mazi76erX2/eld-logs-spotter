import os

from .base import *

DEBUG = False

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOST_DNS", "").split(" ")

# For admin static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
CSRF_TRUSTED_ORIGINS = ["http://localhost:1337"]
