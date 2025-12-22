import os

from decouple import Csv, config

import cloudinary
import cloudinary.uploader

from .base import *

DEBUG = config("DEBUG", default=False, cast=bool)

# Security settings
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Make sure ALLOWED_HOSTS is always set properly
ALLOWED_HOSTS: list[str] = config(
    "ALLOWED_HOSTS",
    default="eld-logs.onrender.com,eld-logs-spotter.vercel.app,.onrender.com,.vercel.app,localhost,127.0.0.1",
    cast=Csv(),
)

# For admin static files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Add your actual domain(s) here
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="https://eld-logs-spotter.vercel.app,https://eld-logs-api.onrender.com",
    cast=Csv(),
)

# CORS Settings
CORS_ALLOWED_ORIGINS: list[str] = config(
    "CORS_ALLOWED_ORIGINS",
    default="https://eld-logs-spotter.vercel.app,http://localhost:3000",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

# Cloudinary Configuration
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": config("CLOUDINARY_CLOUD_NAME"),
    "API_KEY": config("CLOUDINARY_API_KEY"),
    "API_SECRET": config("CLOUDINARY_API_SECRET"),
}

# Initialize Cloudinary
cloudinary.config(
    cloud_name=CLOUDINARY_STORAGE["CLOUD_NAME"],
    api_key=CLOUDINARY_STORAGE["API_KEY"],
    api_secret=CLOUDINARY_STORAGE["API_SECRET"],
    secure=True,
)

# Add cloudinary to installed apps
INSTALLED_APPS += ["cloudinary_storage", "cloudinary"]  # noqa: F405


# Use Cloudinary for media files
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

# Cloudinary media URL (auto-generated)
MEDIA_URL = f"https://res.cloudinary.com/{CLOUDINARY_STORAGE['CLOUD_NAME']}/"

# Static files with WhiteNoise
MIDDLEWARE.insert(2, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.channels": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "channels": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "route_calculator": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "gunicorn": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
