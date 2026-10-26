"""Mocked-data tests for city comparison and local forecast-day coverage."""

import unittest
from datetime import datetime, timedelta, timezone
import json
import threading
from http import HTTPStatus
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch
from pathlib import Path
from urllib.error import URLError

import dashboard_server
from dashboard_server import (
    build_city_comparison_entry,
    build_city_comparison_response,
    prepare_local_forecast,
)
from weather_api import fetch_weather_snapshot


def forecast_payload(city="Pune", offset=0.0, timezone_name="Asia/Kolkata", missing_time=None, current_time="2026-10-26T00:00:00Z"):
    start = datetime(2026, 10, 26, 0, tzinfo=timezone.utc)
    hourly = []
    for index in range(6 * 24):
        stamp = start + timedelta(hours=index)
        stamp_text = stamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        if stamp_text == missing_time:
            continue
        local_hour = (stamp.hour + 5) % 24 if timezone_name == "Asia/Kolkata" else stamp.hour
        if local_hour < 6:
            wbgt = 26.0 + offset
        elif 10 <= local_hour < 18:
            wbgt = 31.0 + offset + (3.0 if local_hour == 14 else 0.0)
        else:
            wbgt = 29.0 + offset
        hourly.append({"time": stamp_text, "wbgt": wbgt, "temperature_c": wbgt - 4.0, "converged": True})
    return {
        "location": {"city": city, "latitude": 18.5, "longitude": 73.8, "timezone": timezone_name, "country": "India"},
        "current": {"time": current_time, "wbgt": 28.0, "mortalityRiskIndex": 35.0, "relativeRisk": 1.0, "attributableFraction": 0.0},
        "hourly": hourly,
        "forecast": [],
    }


class LocalForecastWindowTests(unittest.TestCase):
    def test_fifth_local_day_receives_all_24_hours_from_extended_utc_horizon(self):
        prepared = prepare_local_forecast(forecast_payload(), day_limit=5)
        self.assertEqual(prepared["availableLocalDays"], 5)
        self.assertEqual([day["validHours"] for day in prepared["coverageDays"]], [18, 24, 24, 24, 24])
        self.assertTrue(all(day["complete"] for day in prepared["coverageDays"]))
        fifth_day = prepared["coverageDays"][4]["date"]
        fifth_hours = [item for item in prepared["hourly"] if item["time"] and item["time"]]
        fifth_hours = [item for item in fifth_hours if datetime.fromisoformat(item["time"].replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=5, minutes=30))).date().isoformat() == fifth_day]
        self.assertEqual(len(fifth_hours), 24)

    def test_timezone_changes_local_date_but_hourly_utc_instants_remain_source_values(self):
        india = prepare_local_forecast(forecast_payload(timezone_name="Asia/Kolkata"))
        utc = prepare_local_forecast(forecast_payload(timezone_name="UTC"))
        self.assertNotEqual(india["coverageDays"][0]["validHours"], utc["coverageDays"][0]["validHours"])
        self.assertEqual(india["hourly"][0]["time"], "2026-10-26T01:00:00Z")

    def test_partial_current_day_expected_hours_follow_the_local_hour_grid(self):
        prepared = prepare_local_forecast(forecast_payload(current_time="2026-10-26T16:45:00Z"))
        self.assertEqual(prepared["coverageDays"][0]["date"], "2026-10-26")
        self.assertEqual(prepared["coverageDays"][0]["expectedHours"], 2)
        self.assertEqual(prepared["coverageDays"][0]["validHours"], 2)
        self.assertTrue(prepared["coverageDays"][0]["complete"])

    def test_personal_chart_uses_all_day_rows_and_theme_aware_svg_text(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / "dashboard" / "personal-advisor.js").read_text()
        css = (root / "dashboard" / "styles.css").read_text()
        self.assertIn("const bars = valid.map((item, index)", script)
        self.assertIn("renderHourlyRows(selectedItems, timezone)", script)
        self.assertIn("data.forecastCoverage?.days", script)
        self.assertIn(".wbgt-chart text, .comparison-chart text { fill: currentColor; }", css)
        self.assertIn("color: var(--text-muted)", css)
        self.assertIn('[data-theme="dark"] .forecast-data-status.incomplete', css)
        self.assertIn('[data-theme="dark"] .status-banner.error', css)
        self.assertNotIn("About this estimate", script)

    def test_advisor_forecast_does_not_substitute_synthetic_weather_on_upstream_failure(self):
        with patch("weather_api.urlopen", side_effect=URLError("offline")):
            with self.assertRaises(URLError):
                fetch_weather_snapshot(latitude=18.5, longitude=73.8, forecast_days=6, allow_offline_fallback=False)

    def test_missing_hour_is_reported_and_day_breaks_elevated_run(self):
        payload = forecast_payload()
        # Remove one forecast point from the third local day.
        payload["hourly"] = [item for item in payload["hourly"] if item["time"] != "2026-10-28T05:00:00Z"]
        entry = build_city_comparison_entry(payload)
        self.assertIn("2026-10-28", entry["coverage"]["incompleteDays"])
        self.assertLess(entry["coverage"]["availableHours"], entry["coverage"]["expectedHours"])
        self.assertLess(entry["elevatedRun"]["days"], 5)


class CityComparisonMetricTests(unittest.TestCase):
    def test_all_five_metrics_use_calculated_hourly_values(self):
        payload = forecast_payload()
        entry = build_city_comparison_entry(payload)
        valid = [item for item in entry["hourly"] if item.get("wbgt") is not None]
        self.assertAlmostEqual(entry["peak"]["wbgt"], max(item["wbgt"] for item in valid))
        self.assertEqual(entry["peak"]["time"], max(valid, key=lambda item: item["wbgt"])["time"])
        self.assertEqual(entry["highStress"]["hours"], sum(item["wbgt"] >= 29.5 for item in valid))
        self.assertEqual(entry["elevatedRun"]["days"], 5)
        self.assertIsNotNone(entry["nighttime"]["minimum"]["minimumWbgt"])
        self.assertAlmostEqual(entry["change"]["deltaC"], valid[-1]["wbgt"] - valid[0]["wbgt"], places=1)

    def test_distinct_cities_compare_and_duplicate_coordinates_are_rejected(self):
        locations = [
            {"city": "Pune", "latitude": 18.5, "longitude": 73.8, "country_code": "IN", "timezone": "Asia/Kolkata"},
            {"city": "Mumbai", "latitude": 19.0, "longitude": 72.8, "country_code": "IN", "timezone": "Asia/Kolkata"},
        ]
        with patch("dashboard_server.geocode_city", side_effect=locations), patch(
            "dashboard_server.get_cached_personal_forecast",
            side_effect=[forecast_payload("Pune"), forecast_payload("Mumbai", offset=1.0)],
        ):
            result = build_city_comparison_response(["Pune", "Mumbai"])
        self.assertEqual(len(result["cities"]), 2)
        self.assertEqual(result["methodology"]["highStressThresholdWbgt"], 29.5)

        duplicate = [locations[0], dict(locations[0], city="Poona")]
        with patch("dashboard_server.geocode_city", side_effect=duplicate), self.assertRaisesRegex(ValueError, "distinct"):
            build_city_comparison_response(["Pune", "Poona"])

    def test_invalid_city_count_and_out_of_country_location_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "exactly two"):
            build_city_comparison_response(["Pune"])
        outside = {"city": "London", "latitude": 51.5, "longitude": -0.1, "country_code": "GB"}
        with patch("dashboard_server.geocode_city", return_value=outside), self.assertRaisesRegex(ValueError, "Indian"):
            build_city_comparison_response(["London", "Mumbai"])


class CityComparisonHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = dashboard_server.create_server(host="127.0.0.1", port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}/api/city-comparison"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_post_route_uses_mocked_forecasts_and_returns_both_cities(self):
        locations = [
            {"city": "Pune", "latitude": 18.5, "longitude": 73.8, "country_code": "IN", "timezone": "Asia/Kolkata"},
            {"city": "Mumbai", "latitude": 19.0, "longitude": 72.8, "country_code": "IN", "timezone": "Asia/Kolkata"},
        ]
        request = Request(self.url, data=json.dumps({"cities": ["Pune", "Mumbai"]}).encode(), headers={"Content-Type": "application/json"})
        with patch("dashboard_server.geocode_city", side_effect=locations), patch(
            "dashboard_server.get_cached_personal_forecast",
            side_effect=[forecast_payload("Pune"), forecast_payload("Mumbai", offset=1.0)],
        ):
            with urlopen(request) as response:
                payload = json.loads(response.read().decode())
                self.assertEqual(response.status, HTTPStatus.OK)
        self.assertEqual([city["location"]["city"] for city in payload["cities"]], ["Pune", "Mumbai"])
        self.assertEqual(len(payload["cities"][0]["hourly"]), len(payload["cities"][1]["hourly"]))

    def test_upstream_failure_returns_useful_gateway_error(self):
        locations = [
            {"city": "Pune", "latitude": 18.5, "longitude": 73.8, "country_code": "IN", "timezone": "Asia/Kolkata"},
            {"city": "Mumbai", "latitude": 19.0, "longitude": 72.8, "country_code": "IN", "timezone": "Asia/Kolkata"},
        ]
        request = Request(self.url, data=json.dumps({"cities": ["Pune", "Mumbai"]}).encode(), headers={"Content-Type": "application/json"})
        with patch("dashboard_server.geocode_city", side_effect=locations), patch(
            "dashboard_server.get_cached_personal_forecast", side_effect=RuntimeError("upstream down")
        ), self.assertRaises(HTTPError) as error:
            urlopen(request)
        self.assertEqual(error.exception.code, HTTPStatus.BAD_GATEWAY)
        message = json.loads(error.exception.read().decode())["error"]
        self.assertIn("temporarily unavailable", message)


if __name__ == "__main__":
    unittest.main()
