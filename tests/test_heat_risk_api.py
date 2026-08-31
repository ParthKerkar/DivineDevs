"""Integration and end-to-end tests for Heat Risk & WBGT API."""

import json
import threading
import time
import unittest
from http import HTTPStatus
from urllib.error import HTTPError
from urllib.request import urlopen

from dashboard_server import create_server
from weather_api import fetch_heat_risk_for_city, fetch_heat_risk_for_coordinates


class HeatRiskPipelineTests(unittest.TestCase):
    """Verify the dynamic weather -> Liljegren WBGT -> epidemiological mortality pipeline."""

    def test_pipeline_for_pune(self):
        result = fetch_heat_risk_for_city("Pune", forecast_days=5)
        self._validate_contract(result, expected_city="Pune")

    def test_pipeline_for_multiple_arbitrary_cities(self):
        test_cities = ["Mumbai", "Delhi", "Jaipur", "Kochi", "Nagpur"]
        for city in test_cities:
            result = fetch_heat_risk_for_city(city, forecast_days=5)
            self._validate_contract(result, expected_city=city)

    def test_pipeline_for_coordinates(self):
        result = fetch_heat_risk_for_coordinates(18.5204, 73.8567, forecast_days=5)
        self._validate_contract(result)

    def _validate_contract(self, result, expected_city=None):
        # 1. Location Block
        self.assertIn("location", result)
        location = result["location"]
        if expected_city:
            self.assertEqual(location["city"].lower(), expected_city.lower())
        self.assertIn("latitude", location)
        self.assertIn("longitude", location)

        # 2. Current Conditions Block (Section 19 Schema)
        self.assertIn("current", result)
        current = result["current"]
        required_current_fields = ["wbgt", "relativeRisk", "attributableFraction", "mortalityRiskIndex", "riskCategory"]
        for field in required_current_fields:
            self.assertIn(field, current, f"Missing field '{field}' in current block")

        if current["wbgt"] is not None:
            self.assertGreaterEqual(current["relativeRisk"], 1.00)
            self.assertGreaterEqual(current["attributableFraction"], 0.0)
            self.assertTrue(0.0 <= current["mortalityRiskIndex"] <= 100.0)
            self.assertIn(current["riskCategory"], ["Low", "Moderate", "High", "Very High", "Extreme"])

        # 3. Forecast Array Block (Section 19 Schema)
        self.assertIn("forecast", result)
        forecast = result["forecast"]
        self.assertEqual(len(forecast), 5, "Expected 5-day forecast horizon")

        for day in forecast:
            self.assertIn("date", day)
            for field in required_current_fields:
                self.assertIn(field, day, f"Missing field '{field}' in forecast entry")
            if day["wbgt"] is not None:
                self.assertGreaterEqual(day["relativeRisk"], 1.00)
                self.assertGreaterEqual(day["attributableFraction"], 0.0)
                self.assertTrue(0.0 <= day["mortalityRiskIndex"] <= 100.0)
                self.assertIn(day["riskCategory"], ["Low", "Moderate", "High", "Very High", "Extreme"])

        # 4. Methodology Block
        self.assertIn("methodology", result)
        self.assertIn("Cheng, Lung, Hwang (2019)", result["methodology"]["reference"])
        self.assertEqual(result["methodology"]["reference_exposure_wbgt_c"], 30.0)
        self.assertEqual(result["methodology"]["threshold_wbgt_c"], 33.0)


class HttpServerApiTests(unittest.TestCase):
    """Verify HTTP API Server routes, query handling, and error codes."""

    @classmethod
    def setUpClass(cls):
        cls.port = 8899
        cls.server = create_server(host="127.0.0.1", port=cls.port)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.2)  # Allow server to bind

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_api_health_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/api/health"
        with urlopen(url) as response:
            self.assertEqual(response.status, HTTPStatus.OK)
            data = json.loads(response.read().decode())
            self.assertEqual(data["status"], "healthy")

    def test_api_heat_risk_city_pune(self):
        url = f"http://127.0.0.1:{self.port}/api/heat-risk?city=Pune"
        with urlopen(url) as response:
            self.assertEqual(response.status, HTTPStatus.OK)
            data = json.loads(response.read().decode())
            self.assertEqual(data["location"]["city"], "Pune")
            self.assertIn("current", data)
            self.assertIn("forecast", data)
            self.assertEqual(len(data["forecast"]), 5)

    def test_api_heat_risk_city_jaipur(self):
        url = f"http://127.0.0.1:{self.port}/api/heat-risk?city=Jaipur"
        with urlopen(url) as response:
            self.assertEqual(response.status, HTTPStatus.OK)
            data = json.loads(response.read().decode())
            self.assertEqual(data["location"]["city"], "Jaipur")

    def test_api_heat_risk_coordinates(self):
        url = f"http://127.0.0.1:{self.port}/api/heat-risk?lat=18.5204&lon=73.8567"
        with urlopen(url) as response:
            self.assertEqual(response.status, HTTPStatus.OK)
            data = json.loads(response.read().decode())
            self.assertIn("current", data)
            self.assertIn("forecast", data)

    def test_api_heat_risk_missing_params_400(self):
        url = f"http://127.0.0.1:{self.port}/api/heat-risk"
        with self.assertRaises(HTTPError) as ctx:
            urlopen(url)
        self.assertEqual(ctx.exception.code, HTTPStatus.BAD_REQUEST)

    def test_api_heat_risk_unknown_city_404(self):
        url = f"http://127.0.0.1:{self.port}/api/heat-risk?city=NonExistentCityXYZ998877112233"
        with self.assertRaises(HTTPError) as ctx:
            urlopen(url)
        self.assertEqual(ctx.exception.code, HTTPStatus.NOT_FOUND)

    def test_legacy_wbgt_endpoint_backward_compatibility(self):
        url = f"http://127.0.0.1:{self.port}/api/wbgt?lat=18.5204&lon=73.8567"
        with urlopen(url) as response:
            self.assertEqual(response.status, HTTPStatus.OK)
            data = json.loads(response.read().decode())
            self.assertIn("current", data)
            self.assertIn("daily_max_wbgt", data)


if __name__ == "__main__":
    unittest.main()
