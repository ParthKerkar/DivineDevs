"""Offline contract tests for the Personal Heat Risk Advisor."""

import unittest
import json
import threading
from http import HTTPStatus
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

import dashboard_server
from dashboard_server import build_personal_heat_risk_response
from weather_api import fetch_heat_risk_for_coordinates, validate_location


def sample_payload():
    times = [
        "2026-10-26T00:00:00Z",
        "2026-10-26T01:00:00Z",
        "2026-10-26T02:00:00Z",
        "2026-10-26T03:00:00Z",
        "2026-10-26T04:00:00Z",
        "2026-10-26T05:00:00Z",
    ]
    values = [30.0, 31.4, 33.2, 31.0, 29.1, 29.0]
    hourly = [{"time": stamp, "wbgt": value, "temperature_c": value - 5,
               "flag": "Red" if value >= 32.2 else "Orange", "converged": True}
              for stamp, value in zip(times, values)]
    return {
        "location": {"city": "Pune", "latitude": 18.52, "longitude": 73.85,
                     "country": "India", "admin1": "Maharashtra", "timezone": "Asia/Kolkata"},
        "current": {"wbgt": 30.0, "relativeRisk": 1.0, "attributableFraction": 0.0,
                    "mortalityRiskIndex": 50.0, "riskCategory": "Moderate", "time": times[0],
                    "converged": True},
        "hourly": hourly,
        "forecast": [{"time": stamp, "date": stamp[:10], "wbgt": value,
                      "relativeRisk": 1.0, "mortalityRiskIndex": 50.0}
                     for stamp, value in zip(times, values)],
        "methodology": {"wbgt_method": "Liljegren (2008) Outdoor WBGT"},
    }


class PersonalHeatRiskTests(unittest.TestCase):
    def setUp(self):
        self.payload = sample_payload()
        self.recommendation_calls = []

    def recommendations(self, payload, audience="PUBLIC", situation_context=None):
        self.recommendation_calls.append((audience, situation_context))
        return {
            "risk_context": {"audience": audience, "overall_heat_health_level": "HIGH"},
            "recommendations": [{"priority": 1, "category": "HYDRATION",
                                 "recommendation": "Drink water regularly.", "reason": "Heat stress."}],
            "engine_metadata": {"ai_personalization_applied": False},
            "insights": [],
        }

    def test_hourly_peak_and_local_daily_maximum_are_derived_from_series(self):
        with patch("dashboard_server.get_cached_personal_forecast", return_value=self.payload), \
             patch("dashboard_server.get_heat_health_recommendations_for_risk_payload", side_effect=self.recommendations):
            result = build_personal_heat_risk_response(city="Pune", situation="student")
        self.assertEqual(result["summary"]["peakForecast"]["wbgt"], 33.2)
        self.assertEqual(result["summary"]["peakForecast"]["time"], "2026-10-26T02:00:00Z")
        self.assertEqual(result["summary"]["currentCategory"], "HIGH")
        self.assertEqual(len(result["hourly"]), 5)
        # India local calendar day maximum includes all the UTC hours on this date.
        self.assertEqual(result["forecast"][0]["wbgt"], 33.2)

    def test_improvement_requires_future_hour_at_least_point_eight_below_current(self):
        with patch("dashboard_server.get_cached_personal_forecast", return_value=self.payload), \
             patch("dashboard_server.get_heat_health_recommendations_for_risk_payload", side_effect=self.recommendations):
            result = build_personal_heat_risk_response(city="Pune", situation="commuter")
        improvement = result["summary"]["improvement"]
        self.assertEqual(improvement["time"], "2026-10-26T04:00:00Z")
        self.assertEqual(improvement["wbgt"], 29.1)
        self.assertIn("0.8°C", improvement["rule"])

    def test_situation_uses_supported_audience_and_context(self):
        with patch("dashboard_server.get_cached_heat_risk_for_city", return_value=self.payload), \
             patch("dashboard_server.get_heat_health_recommendations_for_risk_payload", side_effect=self.recommendations):
            result = build_personal_heat_risk_response(city="Pune", situation="outdoor-worker")
        self.assertEqual(result["situation"]["audience"], "OUTDOOR_WORKER")
        self.assertEqual(self.recommendation_calls[0][0], "OUTDOOR_WORKER")
        self.assertEqual(result["situation"]["label"], "Outdoor worker")

    def test_public_situations_remain_supported_public_audience(self):
        for situation in ("student", "elderly-caregiver", "commuter", "outdoor-exercise", "general-public"):
            with self.subTest(situation=situation), \
                 patch("dashboard_server.get_cached_personal_forecast", return_value=self.payload), \
                 patch("dashboard_server.get_heat_health_recommendations_for_risk_payload", side_effect=self.recommendations):
                response = build_personal_heat_risk_response(city="Pune", situation=situation)
                self.assertEqual(response["situation"]["audience"], "PUBLIC")

    def test_invalid_coordinates_reject_non_finite_values(self):
        for value in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_location(value, 73.8)

    def test_existing_physical_pipeline_returns_calculated_hourly_wbgt(self):
        weather = {
            "latitude": 18.52, "longitude": 73.85, "timezone": "GMT",
            "current": {"time": "2026-10-26T00:00", "temperature_2m": 34.0,
                        "relative_humidity_2m": 55, "wind_speed_10m": 2.4,
                        "shortwave_radiation": 600, "surface_pressure": 1004},
            "hourly": {"time": ["2026-10-26T00:00", "2026-10-26T01:00"],
                       "temperature_2m": [34.0, 35.0], "relative_humidity_2m": [55, 50],
                       "wind_speed_10m": [2.4, 2.8], "shortwave_radiation": [600, 700],
                       "surface_pressure": [1004, 1003]},
        }
        with patch("weather_api.fetch_weather_snapshot", return_value=weather):
            result = fetch_heat_risk_for_coordinates(18.52, 73.85)
        self.assertEqual(len(result["hourly"]), 2)
        self.assertTrue(all(item["converged"] for item in result["hourly"]))
        self.assertIsNotNone(result["hourly"][1]["wbgt"])
        self.assertEqual(result["hourly"][1]["temperature_c"], 35.0)
        self.assertEqual(result["hourly"][1]["time"], "2026-10-26T01:00:00Z")


class PersonalHeatRiskHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = dashboard_server.create_server(host="127.0.0.1", port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}/api/personal-heat-risk"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_post_route_accepts_situation_and_returns_structured_report(self):
        expected = {"summary": {"peakForecast": {"wbgt": 33.2}}, "hourly": sample_payload()["hourly"]}
        request_body = json.dumps({"city": "Pune", "situation": "student"}).encode()
        request = Request(self.url, data=request_body, headers={"Content-Type": "application/json"})
        with patch.object(dashboard_server, "build_personal_heat_risk_response", return_value=expected) as builder:
            with urlopen(request) as response:
                body = json.loads(response.read().decode())
                self.assertEqual(response.status, HTTPStatus.OK)
            self.assertEqual(body["summary"]["peakForecast"]["wbgt"], 33.2)
            builder.assert_called_once_with(city="Pune", audience="PUBLIC", situation="student", timezone_name=None)

    def test_post_route_rejects_unknown_situation(self):
        body = json.dumps({"city": "Pune", "situation": "invented"}).encode()
        request = Request(self.url, data=body, headers={"Content-Type": "application/json"})
        with self.assertRaises(HTTPError) as error:
            urlopen(request)
        self.assertEqual(error.exception.code, HTTPStatus.BAD_REQUEST)


if __name__ == "__main__":
    unittest.main()
