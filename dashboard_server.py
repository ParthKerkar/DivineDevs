"""Small no-dependency server for the live WBGT GIS dashboard.

Run ``python3 dashboard_server.py`` then open http://localhost:8000.
"""
import json
import os
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen

from weather_api import (CURRENT_FIELDS, build_dashboard_payload,
                         calculate_current_wbgt, fetch_weather_snapshot,
                         validate_location)


STATIC_DIRECTORY = os.path.join(os.path.dirname(__file__), "dashboard")
CACHE_SECONDS = 300
_cache = {}

# CC0 geoBoundaries ADM0 geometry (WGS84).  This dataset is also fetched by
# the client to clip the rendered field.  Keeping the grid mask here prevents
# weather calls outside the actual country geometry.
BOUNDARY_PATH = os.path.join(STATIC_DIRECTORY, "india-boundary.geojson")


def india_polygons():
    with open(BOUNDARY_PATH, encoding="utf-8") as source:
        feature = json.load(source)["features"][0]
    geometry = feature["geometry"]
    return geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]


INDIA_POLYGONS = india_polygons()


def point_in_ring(lon, lat, ring):
    inside = False
    for index, (x1, y1) in enumerate(ring):
        x2, y2 = ring[(index + 1) % len(ring)]
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def point_in_india(lon, lat):
    """Test a WGS84 point against the high-resolution country geometry."""
    for polygon in INDIA_POLYGONS:
        if point_in_ring(lon, lat, polygon[0]) and not any(point_in_ring(lon, lat, hole) for hole in polygon[1:]):
            return True
    return False


def spatial_grid_points(step=2.0):
    return [(round(lat, 3), round(lon, 3)) for lat in frange(8, 35, step)
            for lon in frange(68, 97, step) if point_in_india(lon, lat)]


def frange(start, stop, step):
    while start <= stop:
        yield start
        start += step


def dashboard_grid():
    """Return current, genuine WBGT observations for an India-wide grid.

    Open-Meteo accepts coordinate lists in one request.  This avoids browser
    fan-out and gives the map one authoritative backend-generated data source.
    """
    key = "india-grid"
    cached = _cache.get(key)
    if cached and time.time() - cached["created"] < CACHE_SECONDS:
        return cached["payload"]
    points = spatial_grid_points()
    params = {"latitude": ",".join(str(p[0]) for p in points),
              "longitude": ",".join(str(p[1]) for p in points),
              "current": ",".join(CURRENT_FIELDS), "timezone": "GMT",
              "wind_speed_unit": "ms"}
    with urlopen("https://api.open-meteo.com/v1/forecast?" + urlencode(params), timeout=25) as response:
        snapshots = json.loads(response.read().decode("utf-8"))
    if not isinstance(snapshots, list):
        snapshots = [snapshots]
    observations = []
    for requested, snapshot in zip(points, snapshots):
        lat, lon = snapshot.get("latitude", requested[0]), snapshot.get("longitude", requested[1])
        current = calculate_current_wbgt(snapshot, lat, lon)
        if current["wbgt_c"] is not None:
            observations.append({"lat": lat, "lon": lon, "wbgt_c": current["wbgt_c"], "risk": current["risk"]})
    payload = {"points": observations, "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    _cache[key] = {"created": time.time(), "payload": payload}
    return payload


def geocode_city(query):
    url = "https://geocoding-api.open-meteo.com/v1/search?" + urlencode({"name": query, "count": 8, "language": "en", "format": "json"})
    with urlopen(url, timeout=12) as response:
        results = json.loads(response.read().decode("utf-8")).get("results", [])
    # Retaining country avoids an ambiguous name silently jumping abroad.
    return [{"name": item["name"], "admin1": item.get("admin1", ""), "country": item.get("country", ""),
             "lat": item["latitude"], "lon": item["longitude"]}
            for item in results if item.get("country_code") == "IN"]


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
        if parsed.path not in {"/api/wbgt", "/api/wbgt-grid", "/api/search"}:
            return super().do_GET()
        try:
            query = parse_qs(parsed.query)
            if parsed.path == "/api/wbgt-grid":
                result = dashboard_grid()
            elif parsed.path == "/api/search":
                term = query.get("q", [""])[0].strip()
                if len(term) < 2: raise ValueError("Enter at least two characters.")
                result = {"results": geocode_city(term)}
            else:
                latitude, longitude = float(query["lat"][0]), float(query["lon"][0])
                validate_location(latitude, longitude)
                result = dashboard_for_location(latitude, longitude)
            body, status = json.dumps(result).encode(), HTTPStatus.OK
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
