"""Small no-dependency server for the live WBGT GIS dashboard.

Run ``python3 dashboard_server.py`` then open http://localhost:8000.
"""
import json
import os
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from weather_api import build_dashboard_payload, fetch_weather_snapshot, validate_location


STATIC_DIRECTORY = os.path.join(os.path.dirname(__file__), "dashboard")
CACHE_SECONDS = 300
_cache = {}


def dashboard_for_location(latitude, longitude):
    """Fetch/calculate one location, caching briefly for map refreshes."""
    key = (round(latitude, 4), round(longitude, 4))
    cached = _cache.get(key)
    if cached and time.time() - cached["created"] < CACHE_SECONDS:
        return cached["payload"]
    payload = build_dashboard_payload(fetch_weather_snapshot(latitude=latitude, longitude=longitude), latitude, longitude)
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _cache[key] = {"created": time.time(), "payload": payload}
    return payload


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIRECTORY, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/wbgt":
            return super().do_GET()
        try:
            query = parse_qs(parsed.query)
            latitude, longitude = float(query["lat"][0]), float(query["lon"][0])
            validate_location(latitude, longitude)
            body, status = json.dumps(dashboard_for_location(latitude, longitude)).encode(), HTTPStatus.OK
        except (KeyError, ValueError) as error:
            body, status = json.dumps({"error": f"Invalid location: {error}"}).encode(), HTTPStatus.BAD_REQUEST
        except Exception as error:  # Keep Open-Meteo/upstream errors visible in the dashboard.
            body, status = json.dumps({"error": f"Could not update WBGT: {error}"}).encode(), HTTPStatus.BAD_GATEWAY
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print("WBGT GIS dashboard: http://localhost:8000")
    ThreadingHTTPServer(("", 8000), DashboardHandler).serve_forever()
