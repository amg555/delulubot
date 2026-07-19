from __future__ import annotations

import asyncio
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from . import config
from .api_clients import _test_apis


class _WebhookHandler(BaseHTTPRequestHandler):
    """Handles both healthcheck (GET) and Telegram updates (POST)."""

    def do_GET(self):
        if self.path == "/dbg":
            body = _test_apis().encode()
        else:
            body = b"OK" if config._bot_alive else b"STARTING"
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        if self.path != f"/{config.TELEGRAM_TOKEN}":
            self.send_response(404)
            self.end_headers()
            return
        try:
            data = json.loads(raw)
            if config._loop and config._application:
                asyncio.run_coroutine_threadsafe(
                    _process_webhook_update(data), config._loop
                )
            self.send_response(200)
        except Exception:
            self.send_response(400)
        self.end_headers()

    def log_message(self, *a):
        pass


async def _process_webhook_update(data: dict):
    """Process a Telegram update received via webhook."""
    try:
        from telegram import Update
        if config._application is None:
            return
        update = Update.de_json(data, config._application.bot)
        await config._application.process_update(update)
    except Exception as e:
        config._last_error = f"{type(e).__name__}: {e}"
        config.logger.error(f"Webhook update error: {config._last_error}", exc_info=True)


def start_webhook_server() -> HTTPServer:
    """Start the combined webhook + healthcheck server and return it."""
    server = HTTPServer(("0.0.0.0", config.PORT), _WebhookHandler)
    import threading
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    config.logger.info(f"Webhook/healthcheck server on port {config.PORT}")

    hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
    if hostname:

        def _keepalive():
            import requests
            import time
            url = f"https://{hostname}/"
            while True:
                time.sleep(840)
                try:
                    requests.get(url, timeout=30)
                except Exception:
                    pass

        threading.Thread(target=_keepalive, daemon=True).start()
        config.logger.info("Self-keepalive started (every 14 min)")

    return server
