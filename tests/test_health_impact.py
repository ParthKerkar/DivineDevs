"""Offline unit tests for published-parameter health-impact indicators."""
import unittest

from health_impact.service import (
    build_health_impact, calculate_ihi, classify_climate_zone, ihi_comfort_class,
)


def hourly_day(day, temperature, ihi_inputs=True):
    """One representative hourly record; sufficient for daily aggregation tests."""
    return {"time": f"2026-05-{day:02d}T12:00:00Z", "tair_c": temperature,
            "rh_pct": 50 if ihi_inputs else None, "solar_wm2": 500 if ihi_inputs else None,
            "wind_ms": 2 if ihi_inputs else None}


class HealthImpactTests(unittest.TestCase):
    def test_ihi_formula(self):
        self.assertAlmostEqual(calculate_ihi(30, 50, 500, 2), 0.820 * 30 + .123 * 50 + .004 * 500 - .117 * 2 - 6.727)

    def test_climate_zone_point_in_polygon(self):
        self.assertEqual(classify_climate_zone(28.6139, 77.2090), "semiarid")
        self.assertEqual(classify_climate_zone(25.3176, 82.9739), "humid_subtropical")
        self.assertEqual(classify_climate_zone(13.0827, 80.2707), "tropical_wet_and_dry")

    def test_every_comfort_boundary_and_mountain_unsupported(self):
        cases = {"arid": (22.9, 26.0, 28.8, 31.4), "semiarid": (23.0, 25.5, 28.0, 30.5),
                 "humid_subtropical": (22.5, 25.4, 27.7, 30.2), "tropical_wet": (23.5, 25.1, 26.7, 28.5),
                 "tropical_wet_and_dry": (23.8, 25.8, 28.1, 30.5)}
        for zone, (comfortable, warm, hot, very_hot) in cases.items():
            self.assertEqual(ihi_comfort_class(comfortable, zone), "comfortable")
            self.assertEqual(ihi_comfort_class(warm, zone), "warm")
            self.assertEqual(ihi_comfort_class(hot, zone), "hot")
            self.assertEqual(ihi_comfort_class(very_hot, zone), "very_hot")
            self.assertEqual(ihi_comfort_class(very_hot + .01, zone), "sweltering")
        self.assertEqual(ihi_comfort_class(40, "mountainous"), "unsupported")

    def test_published_sweltering_effect_and_per_unit_index(self):
        # Daily IHI for these inputs is well above all three sweltering thresholds.
        series = [hourly_day(1, 30), hourly_day(2, 42)]
        expected = [(28.6139, 77.2090, 1.059), (25.3176, 82.9739, 1.081), (13.0827, 80.2707, 1.080)]
        for lat, lon, rr in expected:
            outcome = build_health_impact(series, lat, lon)
            day = outcome["mortality"]["forecast"][0]
            self.assertTrue(day["mortality_effect_available"])
            self.assertEqual(day["relative_risk_per_ihi_c"], rr)
            self.assertEqual(day["mortality_index_per_ihi_c"], round(100 * rr, 1))
            self.assertIsNone(day["mortality_rr"])

    def test_very_hot_and_unsupported_mortality_classes(self):
        # 34°C, 50% RH, 500 W/m², 2 m/s produces IHI 29.07: very hot in Delhi.
        series = [hourly_day(1, 30), hourly_day(2, 34)]
        day = build_health_impact(series, 28.6139, 77.2090)["mortality"]["forecast"][0]
        self.assertEqual(day["ihi_class"], "very_hot")
        self.assertEqual(day["mortality_effect_percent_per_ihi_c"], 3.4)
        cool = build_health_impact([hourly_day(1, 30), hourly_day(2, 22)], 28.6139, 77.2090)["mortality"]["forecast"][0]
        self.assertFalse(cool["mortality_effect_available"])
        self.assertIsNone(cool["relative_risk_per_ihi_c"])

    def test_hospitalization_threshold_and_aggregation(self):
        # D0 plus D+1…D+5: spikes are false, true, true, false, true.
        series = [hourly_day(1, 30)] + [hourly_day(day, temp) for day, temp in zip(range(2, 7), (38.9, 39, 40, 38, 39))]
        hospital = build_health_impact(series, 28.6139, 77.2090)["hospitalization"]
        self.assertFalse(hospital["forecast"][0]["hospitalization_spike"])
        self.assertTrue(hospital["forecast"][1]["hospitalization_spike"])
        self.assertEqual(hospital["forecast"][1]["hospitalization_rr"], 1.186)
        self.assertEqual(hospital["forecast"][1]["hospitalization_stress_index"], 118.6)
        self.assertEqual(hospital["spike_days_next_5"], 3)
        self.assertEqual(hospital["longest_spike_run"], 2)
        self.assertEqual(hospital["first_predicted_spike_day"], "2026-05-03")

    def test_missing_ihi_data_and_outside_india(self):
        outcome = build_health_impact([hourly_day(1, 30), hourly_day(2, 42, ihi_inputs=False)], 28.6139, 77.2090)
        self.assertIsNone(outcome["mortality"]["forecast"][0]["daily_max_ihi"])
        self.assertIsNone(outcome["mortality"]["forecast"][0]["ihi_class"])
        with self.assertRaisesRegex(ValueError, "limited to India"):
            classify_climate_zone(51.5, -0.1)

    def test_ihi_validity_flag(self):
        outcome = build_health_impact([hourly_day(1, 30), hourly_day(2, 15)], 28.6139, 77.2090)
        self.assertFalse(outcome["hourly_ihi"][1]["validity"]["within_published_range"])
        self.assertIsNone(outcome["hourly_ihi"][1]["ihi_c"])
