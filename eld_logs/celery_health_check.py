#!/usr/bin/env python
"""
Run Celery worker with a simple HTTP health check server.
This is a hack for web service using render.com, which expects a web server
to be running for health checks.
"""

import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(b"OK")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass


def run_health_server(port):
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


if __name__ == "__main__":
    from celery.bin import worker

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eld_logs.settings.production")

    import django

    django.setup()

    from eld_logs.celery import app

    port = int(os.environ.get("PORT", 10000))

    health_thread = threading.Thread(
        target=run_health_server, args=(port,), daemon=True
    )
    health_thread.start()
    print(f"Health check server running on port {port}")

    worker = app.Worker(loglevel="INFO", queues=["default", "maps"], concurrency=2)
    worker.start()
