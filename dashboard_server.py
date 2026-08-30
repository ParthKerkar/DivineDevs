"""Small no-dependency server for the live WBGT GIS dashboard.

Run ``python3 dashboard_server.py`` then open http://localhost:8000.
"""
import csv
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
MORTALITY_TOWN_FILE = os.path.join(os.path.dirname(__file__), "mortality_risk", "outputs", "demographic_vulnerability_town.csv")
MORTALITY_CITY_CONFIG = {
    "Pune": ("MAHARASHTRA", "Pune (M Corp.)"), "Mumbai": ("MAHARASHTRA", "Greater Mumbai (M Corp.) (Part)"),
    "Ahmedabad": ("GUJARAT", "Ahmadabad (M Corp.)"), "Chennai": ("TAMIL NADU", "Chennai (M Corp.)"),
    "Kolkata": ("WEST BENGAL", "Kolkata (M Corp.)"),
}


def mortality_band(score):
    if score < 10: return "Low"
    if score < 30: return "Moderate"
    if score < 60: return "High"
    return "Very high"


def load_town_demographics():
    """Load reproducibly generated Census town vulnerability rows by exact name."""
    if not os.path.isfile(MORTALITY_TOWN_FILE):
        raise FileNotFoundError("Town demographic output is missing; run mortality_risk/build_mortality_risk.py first.")
    with open(MORTALITY_TOWN_FILE, encoding="utf-8", newline="") as source:
        return {(row["state_key"], row["town"]): row for row in csv.DictReader(source)}


def mortality_risk_for_city(city, latitude, longitude):
    """Combine a configured Census town score with the cached forecast WBGT."""
    if city not in MORTALITY_CITY_CONFIG:
        raise KeyError(f"No unambiguous Census town match is configured for {city}.")
    state_key, town = MORTALITY_CITY_CONFIG[city]
    demographic = load_town_demographics().get((state_key, town))
    if demographic is None:
        raise KeyError(f"No demographic record found for {town}.")
    valid = [item for item in dashboard_for_location(latitude, longitude)["hourly"] if item["wbgt_c"] is not None]
    if not valid:
        raise RuntimeError("No converged WBGT forecast values are available.")
    peak = max(valid, key=lambda item: item["wbgt_c"])
    thermal_hazard = max(0.0, min(1.0, (peak["wbgt_c"] - 26.0) / 6.2))
    score = 100 * float(demographic["town_demographic_vulnerability_0_1"]) * thermal_hazard
    return {"city": city, "town": town, "state": demographic["state"],
            "demographic_vulnerability_0_100": 100 * float(demographic["town_demographic_vulnerability_0_1"]),
            "forecast_peak_wbgt_c": peak["wbgt_c"], "forecast_peak_time_utc": peak["time"],
            "thermal_hazard_0_100": 100 * thermal_hazard, "mortality_risk_factor_0_100": score,
            "mortality_risk_band": mortality_band(score)}


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
        if parsed.path not in {"/api/wbgt", "/api/mortality-risk"}:
            return super().do_GET()
        try:
            query = parse_qs(parsed.query)
            latitude, longitude = float(query["lat"][0]), float(query["lon"][0])
            validate_location(latitude, longitude)
            if parsed.path == "/api/mortality-risk":
                body, status = json.dumps(mortality_risk_for_city(query["city"][0], latitude, longitude)).encode(), HTTPStatus.OK
            else:
                body, status = json.dumps(dashboard_for_location(latitude, longitude)).encode(), HTTPStatus.OK
        except (KeyError, ValueError) as error:
            body, status = json.dumps({"error": f"Invalid location: {error}"}).encode(), HTTPStatus.BAD_REQUEST
        except FileNotFoundError as error:
            body, status = json.dumps({"error": str(error)}).encode(), HTTPStatus.SERVICE_UNAVAILABLE
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
