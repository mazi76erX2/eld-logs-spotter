from .base import *

from decouple import Csv, config

ALLOWED_HOSTS: list[str] = config(
    "ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv()
)

# define which origins are allowed
CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]

# INSTALLED_APPS += [
#     "debug_toolbar",
# ]

# MIDDLEWARE += [
#     "debug_toolbar.middleware.DebugToolbarMiddleware",
# ]

INTERNAL_IPS = [
    # ...
    "127.0.0.1",
    # ...
]
