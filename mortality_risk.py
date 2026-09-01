"""Epidemiological Heat-Associated Mortality Risk Estimation Module.

Scientific Reference:
--------------------
Cheng, Y.-T., Lung, S.-C. C., & Hwang, J.-S. (2019).
"New approach to identifying proper thresholds for a heat warning system
using health risk increments."
Environmental Research, 169, 180-189.
DOI: 10.1016/j.envres.2018.12.059

Methodological Overview:
-----------------------
1. Exposure Metric: Outdoor Wet-Bulb Globe Temperature (WBGT in Â°C).
2. Health Outcome: All-cause mortality (and heat-associated health risks).
3. Reference Exposure: 30.0Â°C WBGT baseline reference.
   At WBGT <= 30.0Â°C, the modeled Relative Risk (RR) is 1.00 (baseline exposure).
4. Threshold Candidate: 33.0Â°C WBGT.
   The study identified 33.0Â°C WBGT as the mortality-related threshold candidate,
   at which the all-cause mortality risk increment is 9% (RR = 1.09, RaRR = 1.09).
5. Exposure-Response Function:
   - For WBGT <= 30.0Â°C:
       RR = 1.00 (Reference exposure / baseline)
   - For 30.0Â°C < WBGT <= 33.0Â°C:
       RR = exp(beta_1 * (WBGT - 30.0))
       where beta_1 = ln(1.09) / (33.0 - 30.0) â‰ˆ 0.028735 per Â°C.
   - For WBGT > 33.0Â°C:
       RR = 1.09 * exp(beta_2 * (WBGT - 33.0))
       where beta_2 = 2 * beta_1 â‰ˆ 0.057470 per Â°C (exponential risk acceleration
       under extreme thermal strain).
6. Attributable Fraction (AF):
   AF = (RR - 1.0) / RR  (for RR >= 1.0; 0.0 otherwise).
   Represents the proportion of health risk attributable to thermal exposure above baseline.
7. Mortality Risk Index (MRI):
   Application-level normalized index on a continuous 0â€“100 scale:
   - WBGT <= 28.0Â°C: MRI in [0, 20] (Low thermal strain)
   - 28.0Â°C < WBGT <= 30.0Â°C: MRI in (20, 35] (Approaching reference baseline)
   - 30.0Â°C < WBGT <= 33.0Â°C: MRI in (35, 70] (Moderate to High risk approaching threshold)
   - WBGT > 33.0Â°C: MRI in (70, 100] (Very High to Extreme risk exceeding critical threshold)
8. Risk Category Classification:
   - MRI < 30: "Low"
   - 30 <= MRI < 55: "Moderate"
   - 55 <= MRI < 70: "High"
   - 70 <= MRI < 85: "Very High"
   - MRI >= 85: "Extreme"

Scientific Limitations & Contextual Notes:
------------------------------------------
- This model estimates epidemiology-based relative mortality risk based on published
  exposure-response findings from Cheng et al. (2019). It provides a heat-associated
  mortality risk indicator and does NOT claim to predict exact local death counts.
- Indian Context: Choudhary et al. (2024, Environ. Sci. Technol.) documented heat stress
  mortality impacts in India, but utilized the India Heat Index (IHI) rather than WBGT.
  Per epidemiological rigor, IHI coefficients are NOT applied to WBGT.
"""

import math
from typing import Any, Dict, Optional

# Reference Exposure & Thresholds from Cheng et al. (2019)
REFERENCE_WBGT_C: float = 30.0  # Reference baseline where RR = 1.00
THRESHOLD_WBGT_C: float = 33.0  # Mortality threshold candidate (9% excess risk, RR = 1.09)
MORTALITY_INCREMENT_AT_THRESHOLD: float = 0.09  # 9% risk increment

# Log-linear exposure-response slope coefficients
BETA_1: float = math.log(1.0 + MORTALITY_INCREMENT_AT_THRESHOLD) / (THRESHOLD_WBGT_C - REFERENCE_WBGT_C)
BETA_2: float = 2.0 * BETA_1  # Slope for extreme heat above critical threshold


def calculate_relative_risk(wbgt_c: Optional[float]) -> Optional[float]:
    """Calculate epidemiological Relative Risk (RR) from outdoor WBGT (Â°C).

    Returns:
        float: Relative Risk relative to baseline reference exposure (RR >= 1.00),
               or None if WBGT is None.
    """
    if wbgt_c is None:
        return None

    wbgt = float(wbgt_c)
    if wbgt <= REFERENCE_WBGT_C:
        return 1.00
    elif wbgt <= THRESHOLD_WBGT_C:
        return math.exp(BETA_1 * (wbgt - REFERENCE_WBGT_C))
    else:
        return (1.0 + MORTALITY_INCREMENT_AT_THRESHOLD) * math.exp(BETA_2 * (wbgt - THRESHOLD_WBGT_C))


def calculate_attributable_fraction(relative_risk: Optional[float]) -> Optional[float]:
    """Calculate Attributable Fraction (AF) from Relative Risk (RR).

    AF = (RR - 1) / RR for RR >= 1.0, representing the fraction of risk
    attributable to heat exposure under the epidemiological model.

    Returns:
        float: Attributable fraction in [0.0, 1.0), or None if RR is None.
    """
    if relative_risk is None:
        return None
    rr = float(relative_risk)
    if rr <= 1.00:
        return 0.0
    return max(0.0, (rr - 1.0) / rr)


def calculate_mortality_risk_index(wbgt_c: Optional[float], relative_risk: Optional[float] = None) -> Optional[float]:
    """Calculate the normalized 0â€“100 Mortality Risk Index (MRI).

    The mapping is continuous, deterministic, and piecewise-linear across
    key physiological and epidemiological transition points:
      - WBGT <= 28.0Â°C: [0, 20]
      - 28.0Â°C < WBGT <= 30.0Â°C: [20, 35]
      - 30.0Â°C < WBGT <= 33.0Â°C: [35, 70] (RR: 1.00 -> 1.09)
      - WBGT > 33.0Â°C: [70, 100] (RR > 1.09)

    Returns:
        float: Index score in [0.0, 100.0], or None if WBGT is None.
    """
    if wbgt_c is None:
        return None

    wbgt = float(wbgt_c)
    if wbgt <= 0.0:
        return 0.0
    elif wbgt <= 28.0:
        return (wbgt / 28.0) * 20.0
    elif wbgt <= 30.0:
        return 20.0 + ((wbgt - 28.0) / 2.0) * 15.0
    elif wbgt <= 33.0:
        return 35.0 + ((wbgt - 30.0) / 3.0) * 35.0
    else:
        # Above threshold 33Â°C, scales to 100 at 36Â°C WBGT
        return min(100.0, 70.0 + (wbgt - 33.0) * 10.0)


def classify_risk_category(mortality_risk_index: Optional[float]) -> Optional[str]:
    """Classify the Mortality Risk Index into public health risk tiers.

    Categories:
        - None: Unavailable
        - < 30.0: "Low"
        - 30.0 to 55.0: "Moderate"
        - 55.0 to 70.0: "High"
        - 70.0 to 85.0: "Very High"
        - >= 85.0: "Extreme"
    """
    if mortality_risk_index is None:
        return None
    mri = float(mortality_risk_index)
    if mri < 30.0:
        return "Low"
    elif mri < 55.0:
        return "Moderate"
    elif mri < 70.0:
        return "High"
    elif mri < 85.0:
        return "Very High"
    else:
        return "Extreme"


def evaluate_mortality_risk(wbgt_c: Optional[float]) -> Dict[str, Any]:
    """Compute the full epidemiological mortality risk bundle for a given WBGT.

    Returns:
        dict containing:
            - wbgt: WBGT value (Â°C) rounded to 2 decimal places, or None
            - relativeRisk: Modeled Relative Risk (RR >= 1.00), rounded to 4 decimal places
            - attributableFraction: Modeled Attributable Fraction (AF in [0, 1)), rounded to 4 decimal places
            - mortalityRiskIndex: Normalized risk index [0, 100], rounded to 1 decimal place
            - riskCategory: Categorical risk tier ("Low", "Moderate", "High", "Very High", "Extreme")
    """
    if wbgt_c is None:
        return {
            "wbgt": None,
            "relativeRisk": None,
            "attributableFraction": None,
            "mortalityRiskIndex": None,
            "riskCategory": None,
        }

    rr = calculate_relative_risk(wbgt_c)
    af = calculate_attributable_fraction(rr)
    mri = calculate_mortality_risk_index(wbgt_c, rr)
    category = classify_risk_category(mri)

    return {
        "wbgt": round(float(wbgt_c), 2),
        "relativeRisk": round(rr, 4) if rr is not None else None,
        "attributableFraction": round(af, 4) if af is not None else None,
        "mortalityRiskIndex": round(mri, 1) if mri is not None else None,
        "riskCategory": category,
    }


