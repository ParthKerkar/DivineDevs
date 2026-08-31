"""Offline regression tests for the Open-Meteo Liljegren implementation."""
import math
import unittest

from weather_api import (
    build_weather_url,
    build_dashboard_payload,
    calculate_current_wbgt,
    calculate_hourly_wbgt,
    calculate_liljegren_outdoor_wbgt,
    daily_max_wbgt,
    esat,
    risk_category,
)


class LiljegrenRegressionTests(unittest.TestCase):
    """Fixtures independently published by kwodzicki/pywbgt's Liljegren tests.

    PyWBGT's test_liljegren.py fixture uses 2000-06-01T16:00, 33°43'N,
    84°22'W, 2 m wind, and reports its Cython Liljegren results.  This module
    deliberately uses NOAA solar position rather than PyWBGT's SPA, hence a
    0.04 C tolerance.  We first invert the documented log profile so the
    Open-Meteo 10 m input yields that fixture's physical 2 m wind.
    """

    LAT, LON, TIME = 33 + 43 / 60, -(84 + 22 / 60), "2000-06-01T16:00:00Z"
    WIND_RATIO = math.log(2 / .1) / math.log(10 / .1)

    def _run_fixture(self, tair, dewpoint, solar, pressure, wind_2m):
        rh = 100 * esat(dewpoint + 273.15) / esat(tair + 273.15)
        return calculate_liljegren_outdoor_wbgt(
            tair, rh, wind_2m / self.WIND_RATIO, solar, pressure,
            self.TIME, self.LAT, self.LON, avg=1,
        )

    def test_pywbgt_fixture_mild_case(self):
        result = self._run_fixture(25.0, 15.0, 500.0, 985.0, .44704)
        self.assertTrue(result["converged"])
        self.assertAlmostEqual(result["tnwb_c"], 23.320795, delta=.04)
        self.assertAlmostEqual(result["tglobe_c"], 41.970330, delta=.04)
        self.assertAlmostEqual(result["wbgt_c"], 27.218622, delta=.04)

    def test_pywbgt_fixture_hot_case(self):
        result = self._run_fixture(35.0, 25.0, 805.0, 1013.0, 2.23520)
        self.assertTrue(result["converged"])
        self.assertAlmostEqual(result["tnwb_c"], 29.015680, delta=.04)
        self.assertAlmostEqual(result["tglobe_c"], 48.868675, delta=.04)
        self.assertAlmostEqual(result["wbgt_c"], 33.584710, delta=.04)


class WeatherApiContractTests(unittest.TestCase):
    def test_chart_flag_thresholds(self):
        self.assertEqual(risk_category(27.7), "White")
        self.assertEqual(risk_category(27.8), "Green")
        self.assertEqual(risk_category(29.5), "Yellow")
        self.assertEqual(risk_category(31.1), "Red")
        self.assertEqual(risk_category(32.2), "Black")

    def test_url_requests_required_gmt_fields(self):
        url = build_weather_url(18.5196, 73.8554)
        self.assertIn("timezone=GMT", url)
        self.assertIn("shortwave_radiation", url)
        self.assertIn("wind_speed_10m", url)
        self.assertIn("forecast_days=5", url)

    def test_hourly_contract_and_daily_maximum(self):
        data = {
            "latitude": 18.5196, "longitude": 73.8554,
            "hourly": {
                "time": ["2026-08-31T06:00", "2026-08-31T14:00", "2026-09-01T14:00"],
                "temperature_2m": [27.0, 34.2, 32.0],
                "relative_humidity_2m": [70, 58, 60],
                "wind_speed_10m": [2.0, 3.0, 2.5],
                "shortwave_radiation": [120.0, 610.0, 550.0],
                "surface_pressure": [1005.0, 1003.0, 1004.0],
            },
        }
        series = calculate_hourly_wbgt(data)
        self.assertEqual(series[1]["time"], "2026-08-31T14:00:00Z")
        self.assertEqual(set(series[1]), {
            "lat", "lon", "time", "tair_c", "rh_pct", "wind_ms", "solar_wm2",
            "tnwb_c", "tglobe_c", "wbgt_c", "converged", "risk",
            "relative_risk", "attributable_fraction", "mortality_risk_index",
            "epidemiological_risk_category"
        })
        self.assertTrue(series[1]["converged"])
        maxima = daily_max_wbgt(series)
        self.assertEqual([item["time"][:10] for item in maxima], ["2026-08-31", "2026-09-01"])
        self.assertEqual(maxima[0]["time"], "2026-08-31T14:00:00Z")

    def test_dashboard_payload_includes_current_and_forecast(self):
        data = {
            "latitude": 18.5196, "longitude": 73.8554,
            "current": {"time": "2026-08-31T14:00", "temperature_2m": 34.2, "relative_humidity_2m": 58, "wind_speed_10m": 3.0, "shortwave_radiation": 610, "surface_pressure": 1003},
            "hourly": {"time": ["2026-08-31T14:00"], "temperature_2m": [34.2], "relative_humidity_2m": [58], "wind_speed_10m": [3.0], "shortwave_radiation": [610], "surface_pressure": [1003]},
        }
        payload = build_dashboard_payload(data)
        self.assertTrue(payload["current"]["converged"])
        self.assertEqual(len(payload["hourly"]), 1)
        self.assertEqual(len(payload["daily_max_wbgt"]), 1)


if __name__ == "__main__":
    unittest.main()
