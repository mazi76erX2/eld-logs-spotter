#!/usr/bin/env python
"""
Run Celery worker with a simple HTTP health check server.
This is a hack for web service using render.com, which expects a web server to
be running for health checks.
"""
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler


# Health check handler
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass  # Suppress logs


def run_health_server(port):
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


if __name__ == "__main__":
    # Start health check server in background
    port = int(os.environ.get("PORT", 10000))
    health_thread = threading.Thread(
        target=run_health_server, args=(port,), daemon=True
    )
    health_thread.start()
    print(f"Health check server running on port {port}")

    # Start Celery worker
    from celery import current_app
    from celery.bin import worker

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eld_logs.settings.production")

    import django

    django.setup()

    from eld_logs.celery import app

    worker = app.Worker(
        loglevel="INFO",
        queues=["default", "maps"],
        concurrency=2,
    )
    worker.start()
