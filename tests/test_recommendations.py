"""Unit and integration tests for Evidence-Guided AI Recommendation Engine."""

import json
import threading
import time
import unittest
from http import HTTPStatus
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from dashboard_server import create_server
from recommendation_engine import (
    call_ai_personalizer,
    generate_deterministic_recommendations,
    get_heat_health_recommendations,
    get_heat_health_recommendations_for_coords,
    validate_ai_output,
)
from recommendation_library import RECOMMENDATION_LIBRARY, get_library_recommendations
from risk_context_engine import (
    analyze_forecast_trend,
    analyze_heat_persistence,
    build_risk_context,
    get_mri_severity_level,
    get_wbgt_severity_level,
    synthesize_overall_heat_health_level,
)


class RecommendationLibraryTests(unittest.TestCase):
    """Verify library completeness, category conventions, and authoritative citations."""

    def test_library_has_all_audiences(self):
        audiences = {item["audience"] for item in RECOMMENDATION_LIBRARY}
        self.assertEqual(audiences, {"PUBLIC", "OUTDOOR_WORKER", "AUTHORITY"})

    def test_sources_are_authoritative(self):
        valid_sources = {"WHO", "NIOSH", "OSHA"}
        for item in RECOMMENDATION_LIBRARY:
            self.assertIn(item["source"], valid_sources)
            self.assertTrue(len(item["source_reference"]) > 10)
            self.assertTrue(len(item["action"]) > 10)
            self.assertIn(item["priority_base"], [1, 2, 3, 4, 5])

    def test_filtering_by_audience_and_severity(self):
        pub_high = get_library_recommendations("PUBLIC", "HIGH")
        self.assertTrue(len(pub_high) >= 3)
        self.assertTrue(all(item["audience"] == "PUBLIC" for item in pub_high))
        self.assertTrue(all("HIGH" in item["severity_levels"] for item in pub_high))

        wrk_extreme = get_library_recommendations("OUTDOOR_WORKER", "EXTREME")
        self.assertTrue(len(wrk_extreme) >= 3)
        self.assertTrue(all(item["audience"] == "OUTDOOR_WORKER" for item in wrk_extreme))

        auth_very_high = get_library_recommendations("AUTHORITY", "VERY_HIGH")
        self.assertTrue(len(auth_very_high) >= 3)
        self.assertTrue(all(item["audience"] == "AUTHORITY" for item in auth_very_high))


class RiskContextEngineTests(unittest.TestCase):
    """Verify WBGT/MRI tiers, forecast trend math, multi-day persistence, and insights."""

    def test_wbgt_severity_levels(self):
        self.assertEqual(get_wbgt_severity_level(25.0), "LOW")
        self.assertEqual(get_wbgt_severity_level(28.5), "MODERATE")
        self.assertEqual(get_wbgt_severity_level(30.2), "HIGH")
        self.assertEqual(get_wbgt_severity_level(31.5), "VERY_HIGH")
        self.assertEqual(get_wbgt_severity_level(33.0), "EXTREME")

    def test_mri_severity_levels(self):
        self.assertEqual(get_mri_severity_level(15.0), "LOW")
        self.assertEqual(get_mri_severity_level(35.0), "MODERATE")
        self.assertEqual(get_mri_severity_level(60.0), "HIGH")
        self.assertEqual(get_mri_severity_level(75.0), "VERY_HIGH")
        self.assertEqual(get_mri_severity_level(90.0), "EXTREME")

    def test_forecast_trend_detection(self):
        # Rapidly Increasing (+3.0Â°C or more)
        forecast_up_fast = [{"wbgt": 30.0}, {"wbgt": 33.5}, {"wbgt": 34.0}]
        self.assertEqual(analyze_forecast_trend(29.0, forecast_up_fast), "RAPIDLY_INCREASING")

        # Moderately Increasing (+1.0 to 2.9Â°C)
        forecast_up = [{"wbgt": 30.0}, {"wbgt": 31.5}]
        self.assertEqual(analyze_forecast_trend(30.0, forecast_up), "INCREASING")

        # Stable
        forecast_flat = [{"wbgt": 30.0}, {"wbgt": 30.5}]
        self.assertEqual(analyze_forecast_trend(30.2, forecast_flat), "STABLE")

        # Improving (decreasing)
        forecast_down = [{"wbgt": 29.0}, {"wbgt": 27.0}]
        self.assertEqual(analyze_forecast_trend(31.0, forecast_down), "IMPROVING")

    def test_persistence_and_peak_identification(self):
        forecast_data = [
            {"date": "2026-09-01", "wbgt": 28.0, "mortalityRiskIndex": 20.0, "relativeRisk": 1.00},
            {"date": "2026-09-02", "wbgt": 31.5, "mortalityRiskIndex": 55.0, "relativeRisk": 1.044},
            {"date": "2026-09-03", "wbgt": 33.5, "mortalityRiskIndex": 75.0, "relativeRisk": 1.122},
            {"date": "2026-09-04", "wbgt": 32.0, "mortalityRiskIndex": 58.0, "relativeRisk": 1.059},
            {"date": "2026-09-05", "wbgt": 27.0, "mortalityRiskIndex": 18.0, "relativeRisk": 1.00},
        ]
        res = analyze_heat_persistence(forecast_data)
        self.assertEqual(res["elevated_heat_days"], 3)  # Sept 2, 3, 4
        self.assertEqual(res["peak_wbgt"], 33.5)
        self.assertEqual(res["peak_day"], "2026-09-03")
        self.assertEqual(res["peak_mri"], 75.0)

    def test_overall_heat_health_level_synthesis(self):
        # Low + Low -> LOW
        self.assertEqual(synthesize_overall_heat_health_level("LOW", "LOW", "STABLE", 0), "LOW")

        # High WBGT + Moderate MRI -> HIGH
        self.assertEqual(synthesize_overall_heat_health_level("HIGH", "MODERATE", "STABLE", 1), "HIGH")

        # Moderate WBGT + Very High MRI -> VERY_HIGH
        self.assertEqual(synthesize_overall_heat_health_level("MODERATE", "VERY_HIGH", "STABLE", 1), "VERY_HIGH")

        # Moderate + Persistent Heat (3 days) -> escalates to HIGH
        self.assertEqual(synthesize_overall_heat_health_level("MODERATE", "MODERATE", "STABLE", 3), "HIGH")


class RecommendationEngineTests(unittest.TestCase):
    """Verify deterministic rule generation, MRI influence, AI validation, and fallback."""

    def test_deterministic_public_recommendations(self):
        ctx = build_risk_context(
            current_wbgt=32.0,
            current_mri=65.0,
            current_rr=1.059,
            current_af=0.0558,
            forecast_days=[{"wbgt": 33.0, "mortalityRiskIndex": 70.0, "date": "2026-09-01"}],
            audience="PUBLIC"
        )
        recs = generate_deterministic_recommendations(ctx)
        self.assertTrue(len(recs) >= 4)
        self.assertTrue(all("recommendation" in r and "reason" in r and "source" in r for r in recs))
        # Top priority should be 1
        self.assertEqual(recs[0]["priority"], 1)

    def test_deterministic_worker_recommendations(self):
        ctx = build_risk_context(
            current_wbgt=33.5,
            current_mri=75.0,
            current_rr=1.122,
            current_af=0.1085,
            forecast_days=[{"wbgt": 34.0, "mortalityRiskIndex": 80.0, "date": "2026-09-01"}],
            audience="OUTDOOR_WORKER"
        )
        recs = generate_deterministic_recommendations(ctx)
        categories = {r["category"] for r in recs}
        self.assertIn("REST_RECOVERY", categories)
        self.assertIn("HYDRATION", categories)
        self.assertIn("WORK_SCHEDULING", categories)

    def test_mri_severity_influences_urgency(self):
        # Context with low MRI
        ctx_low_mri = build_risk_context(
            current_wbgt=29.0, current_mri=25.0, current_rr=1.00, current_af=0.0,
            forecast_days=[], audience="PUBLIC"
        )
        recs_low = generate_deterministic_recommendations(ctx_low_mri)

        # Context with extreme MRI
        ctx_high_mri = build_risk_context(
            current_wbgt=33.0, current_mri=85.0, current_rr=1.20, current_af=0.166,
            forecast_days=[], audience="PUBLIC"
        )
        recs_high = generate_deterministic_recommendations(ctx_high_mri)

        # High MRI context must produce stronger reasons and top priority 1
        self.assertEqual(recs_high[0]["priority"], 1)
        self.assertIn("critical", recs_high[0]["reason"].lower())

    def test_ai_output_validator_filters_forbidden_content(self):
        approved = [
            {"category": "HYDRATION", "action": "Drink water", "source": "WHO", "source_reference": "WHO Ref"}
        ]
        # AI output containing forbidden medical claims
        hallucinated_ai = [
            {
                "priority": 1,
                "category": "HYDRATION",
                "recommendation": "Take aspirin and prescribe antibiotics for heat symptoms",
                "reason": "Because 50 will die today",
                "source": "WHO",
                "source_reference": "WHO Ref"
            }
        ]
        validated = validate_ai_output(hallucinated_ai, approved)
        # Must discard hallucinated item and return safe approved recommendation
        self.assertEqual(len(validated), 1)
        self.assertNotIn("aspirin", validated[0]["recommendation"].lower())

    def test_end_to_end_recommendation_pipeline_for_city(self):
        result = get_heat_health_recommendations("Pune", audience="PUBLIC", forecast_days=5)
        self.assertIn("location", result)
        self.assertIn("risk_context", result)
        self.assertIn("insights", result)
        self.assertIn("recommendations", result)
        self.assertIn("engine_metadata", result)
        self.assertTrue(len(result["recommendations"]) >= 1)
        self.assertTrue(len(result["insights"]) >= 1)


class RecommendationsApiHttpTests(unittest.TestCase):
    """Verify HTTP API Server GET & POST /api/recommendations routes."""

    @classmethod
    def setUpClass(cls):
        cls.port = 8898
        cls.server = create_server(host="127.0.0.1", port=cls.port)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_get_recommendations_public(self):
        url = f"http://127.0.0.1:{self.port}/api/recommendations?city=Pune&audience=PUBLIC"
        with urlopen(url) as response:
            self.assertEqual(response.status, HTTPStatus.OK)
            data = json.loads(response.read().decode())
            self.assertEqual(data["risk_context"]["audience"], "PUBLIC")
            self.assertIn("recommendations", data)
            self.assertIn("insights", data)

    def test_get_recommendations_worker(self):
        url = f"http://127.0.0.1:{self.port}/api/recommendations?city=Jaipur&audience=OUTDOOR_WORKER"
        with urlopen(url) as response:
            self.assertEqual(response.status, HTTPStatus.OK)
            data = json.loads(response.read().decode())
            self.assertEqual(data["risk_context"]["audience"], "OUTDOOR_WORKER")
            self.assertTrue(len(data["recommendations"]) >= 1)

    def test_get_recommendations_authority(self):
        url = f"http://127.0.0.1:{self.port}/api/recommendations?city=Nagpur&audience=AUTHORITY"
        with urlopen(url) as response:
            self.assertEqual(response.status, HTTPStatus.OK)
            data = json.loads(response.read().decode())
            self.assertEqual(data["risk_context"]["audience"], "AUTHORITY")

    def test_post_recommendations_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/api/recommendations"
        payload = json.dumps({"city": "Kochi, India", "audience": "PUBLIC"}).encode("utf-8")
        req = Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urlopen(req) as response:
            self.assertEqual(response.status, HTTPStatus.OK)
            data = json.loads(response.read().decode())
            self.assertEqual(data["risk_context"]["audience"], "PUBLIC")

    def test_missing_params_error_400(self):
        url = f"http://127.0.0.1:{self.port}/api/recommendations"
        with self.assertRaises(HTTPError) as ctx:
            urlopen(url)
        self.assertEqual(ctx.exception.code, HTTPStatus.BAD_REQUEST)

    def test_unknown_city_error_404(self):
        url = f"http://127.0.0.1:{self.port}/api/recommendations?city=UnknownFakeCity99887711"
        with self.assertRaises(HTTPError) as ctx:
            urlopen(url)
        self.assertEqual(ctx.exception.code, HTTPStatus.NOT_FOUND)


if __name__ == "__main__":
    unittest.main()


