"""
Settings module.

Import from the appropriate settings file based on environment.
Default to local settings.
"""

import os

environment = os.environ.get("DJANGO_SETTINGS_MODULE", "eld_logs.settings.local")

if "production" in environment:
    from .production import *  # noqa: F401, F403
elif "test" in environment:
    from .test import *  # noqa: F401, F403
else:
    from .local import *  # noqa: F401, F403
