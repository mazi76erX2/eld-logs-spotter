"""
WSGI config for eld_logs project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

from decouple import config

DJANGO_SETTINGS_MODULE: str = config(
    "DJANGO_SETTINGS_MODULE",
    default="eld_logs.settings.local",
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", DJANGO_SETTINGS_MODULE)

application = get_wsgi_application()
