"""Small no-dependency server for the live WBGT GIS dashboard.

Run ``python3 dashboard_server.py`` then open http://localhost:8000.
"""
import json
import math
import os
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from weather_api import build_dashboard_payload, fetch_weather_snapshot, validate_location


STATIC_DIRECTORY = os.path.join(os.path.dirname(__file__), "dashboard")
CACHE_SECONDS = int(os.getenv("HEALTH_FORECAST_CACHE_SECONDS", "300"))
_cache = {}

CITY_FILE = os.path.join(os.path.dirname(__file__), "health_impact", "data", "cities.json")


def load_cities():
    """Return the explicit supported-city catalogue; IDs, never names, are keys."""
    with open(CITY_FILE, encoding="utf-8") as source:
        return json.load(source)


def city_by_id(city_id):
    for city in load_cities():
        if city["city_id"] == city_id:
            return city
    raise KeyError(f"Unknown city_id: {city_id}")


def _mean(values):
    valid = _finite_values(values)
    return sum(valid) / len(valid) if valid else None


def _max(values):
    valid = _finite_values(values)
    return max(valid) if valid else None


def _min(values):
    valid = _finite_values(values)
    return min(valid) if valid else None


def _finite_values(values):
    valid = []
    for value in values:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric):
            valid.append(numeric)
    return valid


def _daily_forecast(payload):
    """Join weather/WBGT and health calculations into frontend-ready daily records."""
    days = {}
    for item in payload["hourly"]:
        days.setdefault(item["time"][:10], []).append(item)
    mortality = {item["date"]: item for item in payload["health_impact"]["mortality"]["forecast"]}
    hospital = {item["date"]: item for item in payload["health_impact"]["hospitalization"]["forecast"]}
    forecast = []
    for day in sorted(days)[1:6]:
        records = days[day]
        wbgt_values = [item["wbgt_c"] for item in records]
        wbgt_peak = max((item for item in records if item["wbgt_c"] is not None), key=lambda item: item["wbgt_c"], default=None)
        ihi_values = [item["ihi_c"] for item in records]
        invalid_ihi = [item["ihi_validity"] for item in records if not item["ihi_validity"]["within_published_range"]]
        record = {"date": day,
            "weather": {"temperature_min_c": _min([item["tair_c"] for item in records]), "temperature_max_c": _max([item["tair_c"] for item in records]),
                        "temperature_mean_c": _mean([item["tair_c"] for item in records]), "relative_humidity_percent": _mean([item["rh_pct"] for item in records]),
                        "wind_speed_ms": _mean([item["wind_ms"] for item in records]), "shortwave_radiation_w_m2": _mean([item["solar_wm2"] for item in records])},
            "wbgt": {"wbgt_max_c": _max(wbgt_values), "wbgt_mean_c": _mean(wbgt_values), "wbgt_level": wbgt_peak["risk"] if wbgt_peak else None},
            "ihi": {"ihi_max_c": _max(ihi_values), "ihi_mean_c": _mean(ihi_values), "ihi_class": mortality.get(day, {}).get("ihi_class"),
                    "validity": {"within_published_range": not invalid_ihi, "warnings": [warning for validity in invalid_ihi for warning in validity["warnings"]]}},
            "mortality": mortality.get(day), "hospitalization": hospital.get(day)}
        forecast.append(record)
    return forecast


def build_forecast_response(latitude, longitude, city=None):
    payload = dashboard_for_location(latitude, longitude)
    health = payload["health_impact"]
    forecast = _daily_forecast(payload)
    return {"city": city, "coordinates": {"latitude": latitude, "longitude": longitude},
            "climate_zone": health["mortality"]["climate_zone"], "forecast": forecast,
            "summary": {"max_wbgt_5_day": _max([day["wbgt"]["wbgt_max_c"] for day in forecast]),
                        "max_ihi_5_day": _max([day["ihi"]["ihi_max_c"] for day in forecast]),
                        "sweltering_days": health["mortality"]["sweltering_days_next_5"],
                        "max_mortality_index_per_ihi_c": _max([day["mortality"]["mortality_index_per_ihi_c"] for day in forecast if day["mortality"]]),
                        "hospitalization_spike_days": health["hospitalization"]["spike_days_next_5"],
                        "max_hospitalization_stress_index": health["hospitalization"]["maximum_5_day_hospitalization_stress"]},
            "methodology": {"mortality_index_label": "Published relative-risk multiplier per 1°C IHI increase × 100; not a daily mortality probability or count.",
                "hospitalization_comparison": "Agarwal Table 1: >=39°C vs <38°C; the article narrative also says >=40°C.",
                "vulnerability_score": None},
            "references": {"ihi_mortality": {"authors": "Choudhary et al.", "year": 2024, "doi": "10.1021/acs.est.3c05218"},
                           "hospitalization": {"authors": "Agarwal et al.", "year": 2018, "doi": "10.4103/IJOEM_IJOEM_94_17"},
                           "wbgt": {"method": "Liljegren"}, "weather": {"provider": "Open-Meteo"}}}
def dashboard_for_location(latitude, longitude):
    """Fetch/calculate one location, caching briefly for map refreshes."""
    key = (round(latitude, 4), round(longitude, 4))
    cached = _cache.get(key)
    if cached and time.time() - cached["created"] < CACHE_SECONDS:
        return cached["payload"]
    # Request D0 plus D+1…D+5; the health layer reports the five future days.
    payload = build_dashboard_payload(fetch_weather_snapshot(latitude=latitude, longitude=longitude, forecast_days=6), latitude, longitude)
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _cache[key] = {"created": time.time(), "payload": payload}
    return payload


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIRECTORY, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path_parts = [part for part in parsed.path.split("/") if part]
        city_forecast = len(path_parts) in {4, 5} and path_parts[:2] == ["api", "cities"] and path_parts[3] == "forecast"
        if parsed.path not in {"/api/wbgt", "/api/mortality-risk", "/api/cities", "/api/forecast"} and not city_forecast:
            return super().do_GET()
        try:
            query = parse_qs(parsed.query)
            if parsed.path == "/api/cities":
                body, status = json.dumps(load_cities()).encode(), HTTPStatus.OK
            elif city_forecast:
                city = city_by_id(path_parts[2])
                response = build_forecast_response(city["latitude"], city["longitude"], city)
                if len(path_parts) == 5:
                    requested_date = path_parts[4]
                    matching = next((item for item in response["forecast"] if item["date"] == requested_date), None)
                    if matching is None:
                        raise KeyError(f"Forecast date unavailable: {requested_date}")
                    response["forecast"] = matching
                body, status = json.dumps(response).encode(), HTTPStatus.OK
            else:
                latitude = float((query.get("latitude") or query.get("lat"))[0])
                longitude = float((query.get("longitude") or query.get("lon"))[0])
                validate_location(latitude, longitude)
                if parsed.path == "/api/forecast":
                    body, status = json.dumps(build_forecast_response(latitude, longitude)).encode(), HTTPStatus.OK
                elif parsed.path == "/api/mortality-risk":
                    body, status = json.dumps(dashboard_for_location(latitude, longitude)["health_impact"]["mortality"]).encode(), HTTPStatus.OK
                else:
                    body, status = json.dumps(dashboard_for_location(latitude, longitude)).encode(), HTTPStatus.OK
        except (KeyError, ValueError) as error:
            status = HTTPStatus.NOT_FOUND if isinstance(error, KeyError) else HTTPStatus.BAD_REQUEST
            body = json.dumps({"error": str(error)}).encode()
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
