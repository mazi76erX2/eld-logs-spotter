import os

from .base import *

from decouple import Csv, config


DEBUG = config("DEBUG", default=False, cast=bool)

# Make sure ALLOWED_HOSTS is always set properly
ALLOWED_HOSTS: list[str] = config(
    "ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv()
)

# For admin static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Add your actual domain(s) here
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:1337,http://127.0.0.1:1337",
    cast=Csv(),
)
