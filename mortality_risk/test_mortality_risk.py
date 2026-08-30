import unittest

import pandas as pd

from mortality_risk.build_mortality_risk import capped_percentile_scale, clean_state_name, risk_band


class MortalityRiskUnitTests(unittest.TestCase):
    def test_census_state_aliases_are_normalised(self):
        self.assertEqual(clean_state_name("State - Maharashtra (27)"), "MAHARASHTRA")
        self.assertEqual(clean_state_name("Maharashtra"), "MAHARASHTRA")

    def test_robust_scale_is_bounded(self):
        values = capped_percentile_scale(pd.Series([1, 2, 3, 4, 100]))
        self.assertTrue(((values >= 0) & (values <= 1)).all())

    def test_risk_bands(self):
        self.assertEqual(risk_band(0), "Low")
        self.assertEqual(risk_band(10), "Moderate")
        self.assertEqual(risk_band(30), "High")
        self.assertEqual(risk_band(60), "Very high")


if __name__ == "__main__":
    unittest.main()
