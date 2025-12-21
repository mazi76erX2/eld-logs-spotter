import os

from .local import *  # noqa: F401, F403

# Use in-memory channel layer for tests (no Redis required)
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# Use SQLite for faster tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Use actual values for tests, not environment variable syntax
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")

# Celery: run tasks synchronously in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# If you still need a broker URL, construct it properly:
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

# Or use memory transport for tests:
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

# Faster password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable debug
DEBUG = False

# Media files for tests
import tempfile

MEDIA_ROOT = tempfile.mkdtemp()
