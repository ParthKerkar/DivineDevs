"""HTTP REST API Server for Extreme Heatwave Early Warning & Recommendation System.

Endpoints:
----------
- GET /api/heat-risk?city=<city_name>
- GET /api/heat-risk?lat=<latitude>&lon=<longitude>
- GET /api/recommendations?city=<city_name>&audience=<PUBLIC|OUTDOOR_WORKER|AUTHORITY>
- GET /api/recommendations?lat=<latitude>&lon=<longitude>&audience=<PUBLIC|OUTDOOR_WORKER|AUTHORITY>
- POST /api/recommendations (JSON body: {"city": "Pune", "audience": "OUTDOOR_WORKER"})
- GET /api/wbgt?lat=<latitude>&lon=<longitude> (legacy dashboard support)
- GET /api/health
- GET / (serves interactive GIS dashboard)

Run:
----
python dashboard_server.py
"""

import json
import os
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from geocoding import geocode_city
from recommendation_engine import (
    get_heat_health_recommendations,
    get_heat_health_recommendations_for_coords,
)
from weather_api import (
    build_dashboard_payload,
    fetch_heat_risk_for_city,
    fetch_heat_risk_for_coordinates,
    fetch_weather_snapshot,
    validate_location,
)

STATIC_DIRECTORY = os.path.join(os.path.dirname(__file__), "dashboard")
CACHE_SECONDS = 300  # 5 minutes cache for weather/risk payloads
_dashboard_cache: Dict[Tuple[float, float], Dict[str, Any]] = {}
_heat_risk_cache: Dict[str, Dict[str, Any]] = {}


def get_cached_dashboard(latitude: float, longitude: float) -> Dict[str, Any]:
    """Fetch/calculate legacy dashboard payload with brief caching."""
    key = (round(latitude, 4), round(longitude, 4))
    cached = _dashboard_cache.get(key)
    if cached and (time.time() - cached["created"] < CACHE_SECONDS):
        return cached["payload"]

    payload = build_dashboard_payload(
        fetch_weather_snapshot(latitude=latitude, longitude=longitude),
        latitude,
        longitude
    )
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _dashboard_cache[key] = {"created": time.time(), "payload": payload}
    return payload


def get_cached_heat_risk_for_city(city: str) -> Dict[str, Any]:
    """Fetch/calculate heat risk for any city dynamically with caching."""
    key = city.strip().lower()
    cached = _heat_risk_cache.get(key)
    if cached and (time.time() - cached["created"] < CACHE_SECONDS):
        return cached["payload"]

    payload = fetch_heat_risk_for_city(city)
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _heat_risk_cache[key] = {"created": time.time(), "payload": payload}
    return payload


def get_cached_heat_risk_for_coords(latitude: float, longitude: float) -> Dict[str, Any]:
    """Fetch/calculate heat risk for arbitrary coordinates with caching."""
    key = f"{round(latitude, 4)},{round(longitude, 4)}"
    cached = _heat_risk_cache.get(key)
    if cached and (time.time() - cached["created"] < CACHE_SECONDS):
        return cached["payload"]

    payload = fetch_heat_risk_for_coordinates(latitude, longitude)
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _heat_risk_cache[key] = {"created": time.time(), "payload": payload}
    return payload


class HeatRiskApiHandler(SimpleHTTPRequestHandler):
    """HTTP Request Handler for Heat Risk, WBGT & Recommendation API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIRECTORY, **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def _send_json(self, status: int, data: Dict[str, Any]) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, filename: str, content_type: str) -> None:
        filepath = os.path.join(STATIC_DIRECTORY, filename)
        if not os.path.exists(filepath):
            self.send_error(HTTPStatus.NOT_FOUND, f"File not found: {filename}")
            return
        with open(filepath, "rb") as f:
            content = f.read()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/recommendations":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
                data = json.loads(body)

                city = data.get("city")
                lat = data.get("lat") or data.get("latitude")
                lon = data.get("lon") or data.get("longitude")
                audience = data.get("audience", "PUBLIC")
                days = int(data.get("days", 5))

                if city:
                    payload = get_heat_health_recommendations(city, audience=audience, forecast_days=days)
                    self._send_json(HTTPStatus.OK, payload)
                elif lat is not None and lon is not None:
                    lat_f, lon_f = float(lat), float(lon)
                    validate_location(lat_f, lon_f)
                    payload = get_heat_health_recommendations_for_coords(lat_f, lon_f, audience=audience, forecast_days=days)
                    self._send_json(HTTPStatus.OK, payload)
                else:
                    self._send_json(HTTPStatus.BAD_REQUEST, {
                        "error": "Missing parameter. Please provide 'city' or both 'lat' and 'lon' in JSON body."
                    })
            except ValueError as err:
                status = HTTPStatus.NOT_FOUND if "not found" in str(err).lower() else HTTPStatus.BAD_REQUEST
                self._send_json(status, {"error": str(err)})
            except Exception as err:
                self._send_json(HTTPStatus.BAD_GATEWAY, {
                    "error": f"Failed to generate recommendations: {err}"
                })
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Health Check
        if path == "/api/health":
            self._send_json(HTTPStatus.OK, {
                "status": "healthy",
                "service": "extreme-heatwave-early-warning-backend",
                "version": "2.0.0",
                "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })
            return

        # Heat Risk Primary API
        if path == "/api/heat-risk":
            try:
                city = query.get("city", [None])[0]
                lat_str = query.get("lat", [None])[0] or query.get("latitude", [None])[0]
                lon_str = query.get("lon", [None])[0] or query.get("longitude", [None])[0]

                if city:
                    payload = get_cached_heat_risk_for_city(city)
                    self._send_json(HTTPStatus.OK, payload)
                elif lat_str is not None and lon_str is not None:
                    lat, lon = float(lat_str), float(lon_str)
                    validate_location(lat, lon)
                    payload = get_cached_heat_risk_for_coords(lat, lon)
                    self._send_json(HTTPStatus.OK, payload)
                else:
                    self._send_json(HTTPStatus.BAD_REQUEST, {
                        "error": "Missing parameter. Please provide ?city=<city_name> or ?lat=<lat>&lon=<lon>"
                    })
            except ValueError as err:
                status = HTTPStatus.NOT_FOUND if "not found" in str(err).lower() else HTTPStatus.BAD_REQUEST
                self._send_json(status, {"error": str(err)})
            except Exception as err:
                self._send_json(HTTPStatus.BAD_GATEWAY, {
                    "error": f"Failed to compute heat risk: {err}"
                })
            return

        # Evidence-Guided Recommendations API
        if path == "/api/recommendations":
            try:
                city = query.get("city", [None])[0]
                lat_str = query.get("lat", [None])[0] or query.get("latitude", [None])[0]
                lon_str = query.get("lon", [None])[0] or query.get("longitude", [None])[0]
                audience = query.get("audience", ["PUBLIC"])[0]
                days = int(query.get("days", ["5"])[0])

                if city:
                    payload = get_heat_health_recommendations(city, audience=audience, forecast_days=days)
                    self._send_json(HTTPStatus.OK, payload)
                elif lat_str is not None and lon_str is not None:
                    lat, lon = float(lat_str), float(lon_str)
                    validate_location(lat, lon)
                    payload = get_heat_health_recommendations_for_coords(lat, lon, audience=audience, forecast_days=days)
                    self._send_json(HTTPStatus.OK, payload)
                else:
                    self._send_json(HTTPStatus.BAD_REQUEST, {
                        "error": "Missing parameter. Please provide ?city=<city_name> or ?lat=<lat>&lon=<lon>"
                    })
            except ValueError as err:
                status = HTTPStatus.NOT_FOUND if "not found" in str(err).lower() else HTTPStatus.BAD_REQUEST
                self._send_json(status, {"error": str(err)})
            except Exception as err:
                self._send_json(HTTPStatus.BAD_GATEWAY, {
                    "error": f"Failed to generate recommendations: {err}"
                })
            return

        # Legacy / GIS WBGT API Endpoint
        if path == "/api/wbgt":
            try:
                city = query.get("city", [None])[0]
                lat_str = query.get("lat", [None])[0]
                lon_str = query.get("lon", [None])[0]

                if city:
                    geo = geocode_city(city)
                    lat, lon = geo["latitude"], geo["longitude"]
                elif lat_str is not None and lon_str is not None:
                    lat, lon = float(lat_str), float(lon_str)
                else:
                    self._send_json(HTTPStatus.BAD_REQUEST, {
                        "error": "Missing location. Please provide ?lat=<lat>&lon=<lon> or ?city=<city>"
                    })
                    return

                validate_location(lat, lon)
                payload = get_cached_dashboard(lat, lon)
                self._send_json(HTTPStatus.OK, payload)
            except ValueError as err:
                status = HTTPStatus.NOT_FOUND if "not found" in str(err).lower() else HTTPStatus.BAD_REQUEST
                self._send_json(status, {"error": str(err)})
            except Exception as err:
                self._send_json(HTTPStatus.BAD_GATEWAY, {
                    "error": f"Could not update WBGT: {err}"
                })
            return

        # Direct explicit serving of static files to prevent caching
        if path in ("/", "/index.html"):
            self._serve_file("index.html", "text/html; charset=utf-8")
            return
        elif path == "/styles.css":
            self._serve_file("styles.css", "text/css; charset=utf-8")
            return
        elif path == "/app.js":
            self._serve_file("app.js", "application/javascript; charset=utf-8")
            return

        # Fallback to SimpleHTTPRequestHandler for any other static files
        super().do_GET()


def create_server(host: str = "", port: int = 8000) -> ThreadingHTTPServer:
    """Create and return a configured ThreadingHTTPServer instance."""
    return ThreadingHTTPServer((host, port), HeatRiskApiHandler)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Heat Risk & Recommendation Backend server running at http://localhost:{port}")
    print(f"  - Recommendations API: http://localhost:{port}/api/recommendations?city=Pune&audience=PUBLIC")
    print(f"  - Primary Heat Risk:   http://localhost:{port}/api/heat-risk?city=Pune")
    print(f"  - Health check:        http://localhost:{port}/api/health")
    server = create_server(port=port)
    server.serve_forever()
