from __future__ import absolute_import, unicode_literals

import os
from typing import Any

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.setting.local")

app = Celery("core")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self: Any) -> str:
    """Debug task for testing Celery."""
    return f"Request: {self.request!r}"
