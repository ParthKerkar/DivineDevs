"""Unit tests for Epidemiological Mortality Risk Model (Cheng et al., 2019)."""

import math
import unittest

from mortality_risk import (
    BETA_1,
    BETA_2,
    MORTALITY_INCREMENT_AT_THRESHOLD,
    REFERENCE_WBGT_C,
    THRESHOLD_WBGT_C,
    calculate_attributable_fraction,
    calculate_mortality_risk_index,
    calculate_relative_risk,
    classify_risk_category,
    evaluate_mortality_risk,
)


class MortalityRiskModelTests(unittest.TestCase):
    """Verify epidemiological formulations match Cheng et al. (2019)."""

    def test_constants_and_reference_values(self):
        self.assertEqual(REFERENCE_WBGT_C, 30.0)
        self.assertEqual(THRESHOLD_WBGT_C, 33.0)
        self.assertEqual(MORTALITY_INCREMENT_AT_THRESHOLD, 0.09)
        self.assertAlmostEqual(BETA_1, math.log(1.09) / 3.0, places=6)

    def test_relative_risk_at_reference_and_below(self):
        # Baseline reference exposure
        self.assertEqual(calculate_relative_risk(30.0), 1.00)
        # Below baseline reference exposure
        self.assertEqual(calculate_relative_risk(25.0), 1.00)
        self.assertEqual(calculate_relative_risk(0.0), 1.00)
        self.assertEqual(calculate_relative_risk(-5.0), 1.00)
        # None handling
        self.assertIsNone(calculate_relative_risk(None))

    def test_relative_risk_at_candidate_threshold(self):
        # Exactly at 33.0Â°C threshold candidate from Cheng et al. (2019)
        rr_33 = calculate_relative_risk(33.0)
        self.assertAlmostEqual(rr_33, 1.09, delta=0.0001)

    def test_relative_risk_above_candidate_threshold(self):
        # Moderate elevated heat at 31.5Â°C
        rr_31_5 = calculate_relative_risk(31.5)
        self.assertGreater(rr_31_5, 1.00)
        self.assertLess(rr_31_5, 1.09)
        self.assertAlmostEqual(rr_31_5, math.exp(BETA_1 * 1.5), places=5)

        # Extreme heat at 35.0Â°C
        rr_35 = calculate_relative_risk(35.0)
        self.assertGreater(rr_35, 1.09)
        self.assertAlmostEqual(rr_35, 1.09 * math.exp(BETA_2 * 2.0), places=5)

    def test_attributable_fraction_formula(self):
        # AF = (RR - 1) / RR
        self.assertEqual(calculate_attributable_fraction(1.00), 0.0)
        self.assertEqual(calculate_attributable_fraction(0.95), 0.0)
        self.assertIsNone(calculate_attributable_fraction(None))

        # At threshold RR = 1.09
        af_33 = calculate_attributable_fraction(1.09)
        expected_af = 0.09 / 1.09
        self.assertAlmostEqual(af_33, expected_af, places=5)
        self.assertAlmostEqual(af_33, 0.0825688, delta=0.0001)

        # At RR = 1.25
        af_high = calculate_attributable_fraction(1.25)
        self.assertAlmostEqual(af_high, 0.25 / 1.25, places=5)

    def test_mortality_risk_index_piecewise_continuity(self):
        # Check transition points continuity
        mri_28_below = calculate_mortality_risk_index(28.0)
        mri_28_above = calculate_mortality_risk_index(28.0001)
        self.assertAlmostEqual(mri_28_below, 20.0, places=2)
        self.assertAlmostEqual(mri_28_above, 20.0, places=2)

        mri_30_below = calculate_mortality_risk_index(30.0)
        mri_30_above = calculate_mortality_risk_index(30.0001)
        self.assertAlmostEqual(mri_30_below, 35.0, places=2)
        self.assertAlmostEqual(mri_30_above, 35.0, places=2)

        mri_33_below = calculate_mortality_risk_index(33.0)
        mri_33_above = calculate_mortality_risk_index(33.0001)
        self.assertAlmostEqual(mri_33_below, 70.0, places=2)
        self.assertAlmostEqual(mri_33_above, 70.0, places=2)

        # Extreme upper bound capping at 100
        self.assertEqual(calculate_mortality_risk_index(36.0), 100.0)
        self.assertEqual(calculate_mortality_risk_index(45.0), 100.0)

        # Negative / None handling
        self.assertEqual(calculate_mortality_risk_index(-10.0), 0.0)
        self.assertIsNone(calculate_mortality_risk_index(None))

    def test_risk_category_classification(self):
        self.assertEqual(classify_risk_category(15.0), "Low")
        self.assertEqual(classify_risk_category(29.9), "Low")
        self.assertEqual(classify_risk_category(30.0), "Moderate")
        self.assertEqual(classify_risk_category(54.9), "Moderate")
        self.assertEqual(classify_risk_category(55.0), "High")
        self.assertEqual(classify_risk_category(69.9), "High")
        self.assertEqual(classify_risk_category(70.0), "Very High")
        self.assertEqual(classify_risk_category(84.9), "Very High")
        self.assertEqual(classify_risk_category(85.0), "Extreme")
        self.assertEqual(classify_risk_category(100.0), "Extreme")
        self.assertIsNone(classify_risk_category(None))

    def test_evaluate_mortality_risk_bundle(self):
        bundle_low = evaluate_mortality_risk(25.0)
        self.assertEqual(bundle_low["wbgt"], 25.0)
        self.assertEqual(bundle_low["relativeRisk"], 1.00)
        self.assertEqual(bundle_low["attributableFraction"], 0.0)
        self.assertEqual(bundle_low["riskCategory"], "Low")

        bundle_threshold = evaluate_mortality_risk(33.0)
        self.assertEqual(bundle_threshold["wbgt"], 33.0)
        self.assertEqual(bundle_threshold["relativeRisk"], 1.09)
        self.assertAlmostEqual(bundle_threshold["attributableFraction"], 0.0826, delta=0.001)
        self.assertEqual(bundle_threshold["mortalityRiskIndex"], 70.0)
        self.assertEqual(bundle_threshold["riskCategory"], "Very High")

        bundle_none = evaluate_mortality_risk(None)
        self.assertIsNone(bundle_none["wbgt"])
        self.assertIsNone(bundle_none["relativeRisk"])
        self.assertIsNone(bundle_none["attributableFraction"])
        self.assertIsNone(bundle_none["mortalityRiskIndex"])
        self.assertIsNone(bundle_none["riskCategory"])


if __name__ == "__main__":
    unittest.main()


