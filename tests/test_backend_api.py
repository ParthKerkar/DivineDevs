"""Backend response assembly tests; network weather calls are deliberately mocked."""
import unittest
from unittest.mock import patch

import dashboard_server
from health_impact import build_health_impact


def fixture_payload():
    hourly = []
    for day, temp in enumerate((30, 34, 39, 40, 38, 39), 1):
        hourly.append({"time": f"2026-05-{day:02d}T12:00:00Z", "tair_c": temp, "rh_pct": 50,
                       "wind_ms": 2, "solar_wm2": 500, "wbgt_c": 28.0, "risk": "Green"})
    health = build_health_impact(hourly, 13.0827, 80.2707)
    for source, annotated in zip(hourly, health["hourly_ihi"]):
        source["ihi_c"] = annotated["ihi_c"]
        source["ihi_validity"] = annotated["validity"]
    return {"hourly": hourly, "health_impact": health}


class BackendApiAssemblyTests(unittest.TestCase):
    def test_city_catalog_uses_stable_ids_and_lookup(self):
        chennai = dashboard_server.city_by_id("chennai")
        self.assertEqual(chennai["city_name"], "Chennai")
        self.assertIn("city_id", dashboard_server.load_cities()[0])
        with self.assertRaises(KeyError):
            dashboard_server.city_by_id("not-a-city")

    def test_coordinate_forecast_returns_daily_backend_metrics(self):
        with patch("dashboard_server.dashboard_for_location", return_value=fixture_payload()):
            response = dashboard_server.build_forecast_response(13.0827, 80.2707)
        self.assertEqual(len(response["forecast"]), 5)
        day = response["forecast"][0]
        self.assertEqual(day["date"], "2026-05-02")
        self.assertIn("weather", day)
        self.assertIn("wbgt", day)
        self.assertIn("ihi", day)
        self.assertIn("mortality", day)
        self.assertIn("hospitalization", day)
        self.assertIn("references", response)
        self.assertEqual(response["summary"]["hospitalization_spike_days"], 3)

