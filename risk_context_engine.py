"""Risk Context Engine & Forecast Trend / Persistence Analysis.

Synthesizes physical WBGT, epidemiological Mortality Risk Index (MRI),
Relative Risk (RR), multi-day forecast trajectories, and audience context.
"""

from typing import Any, Dict, List, Optional, Tuple

SEVERITY_ORDER = ["LOW", "MODERATE", "HIGH", "VERY_HIGH", "EXTREME"]
SEVERITY_WEIGHT = {k: i for i, k in enumerate(SEVERITY_ORDER)}


def get_wbgt_severity_level(wbgt_c: Optional[float]) -> str:
    """Map physical outdoor WBGT (Â°C) to documented severity tiers."""
    if wbgt_c is None:
        return "LOW"
    wbgt = float(wbgt_c)
    if wbgt < 27.8:
        return "LOW"
    elif wbgt < 29.5:
        return "MODERATE"
    elif wbgt < 31.1:
        return "HIGH"
    elif wbgt < 32.2:
        return "VERY_HIGH"
    else:
        return "EXTREME"


def get_mri_severity_level(mri: Optional[float]) -> str:
    """Map Mortality Risk Index (0-100) to epidemiological risk tiers."""
    if mri is None:
        return "LOW"
    val = float(mri)
    if val < 30.0:
        return "LOW"
    elif val < 55.0:
        return "MODERATE"
    elif val < 70.0:
        return "HIGH"
    elif val < 85.0:
        return "VERY_HIGH"
    else:
        return "EXTREME"


def analyze_forecast_trend(current_wbgt: Optional[float], forecast_days: List[Dict[str, Any]]) -> str:
    """Determine the forecast trend based on mathematical delta between current and forecast peaks.

    Returns:
        One of: 'RAPIDLY_INCREASING', 'INCREASING', 'STABLE', 'IMPROVING'
    """
    if not forecast_days:
        return "STABLE"

    valid_wbgt_forecasts = [f["wbgt"] for f in forecast_days if f.get("wbgt") is not None]
    if not valid_wbgt_forecasts:
        return "STABLE"

    curr = float(current_wbgt) if current_wbgt is not None else valid_wbgt_forecasts[0]
    max_forecast = max(valid_wbgt_forecasts)
    delta = max_forecast - curr

    if delta >= 3.0:
        return "RAPIDLY_INCREASING"
    elif delta >= 1.0:
        return "INCREASING"
    elif delta <= -1.5:
        return "IMPROVING"
    else:
        return "STABLE"


def analyze_heat_persistence(forecast_days: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate multi-day heat persistence and peak risk timing."""
    if not forecast_days:
        return {
            "elevated_heat_days": 0,
            "peak_wbgt": None,
            "peak_day": None,
            "peak_mri": None,
            "peak_rr": None,
        }

    elevated_count = 0
    peak_wbgt = -999.0
    peak_day = None
    peak_mri = None
    peak_rr = None

    for item in forecast_days:
        wbgt = item.get("wbgt")
        mri = item.get("mortalityRiskIndex")
        rr = item.get("relativeRisk")
        day_date = item.get("date")

        if wbgt is not None:
            # Elevated heat threshold (WBGT >= 29.5Â°C or MRI >= 55.0)
            if wbgt >= 29.5 or (mri is not None and mri >= 55.0):
                elevated_count += 1

            if wbgt > peak_wbgt:
                peak_wbgt = wbgt
                peak_day = day_date
                peak_mri = mri
                peak_rr = rr

    if peak_wbgt == -999.0:
        peak_wbgt = None

    return {
        "elevated_heat_days": elevated_count,
        "peak_wbgt": peak_wbgt,
        "peak_day": peak_day,
        "peak_mri": peak_mri,
        "peak_rr": peak_rr,
    }


def synthesize_overall_heat_health_level(
    wbgt_level: str,
    mri_level: str,
    trend: str,
    elevated_days: int
) -> str:
    """Synthesize WBGT physical strain and MRI epidemiological risk into an overall level."""
    w_wbgt = SEVERITY_WEIGHT.get(wbgt_level, 0)
    w_mri = SEVERITY_WEIGHT.get(mri_level, 0)

    # Base level is the maximum of physical thermal stress and epidemiological risk
    base_weight = max(w_wbgt, w_mri)

    # Escalate if persistent multi-day heat or rapidly increasing trend
    if elevated_days >= 3 and base_weight < 4:
        base_weight = min(4, base_weight + 1)
    elif trend == "RAPIDLY_INCREASING" and base_weight < 4 and base_weight >= 1:
        base_weight = min(4, base_weight + 1)

    return SEVERITY_ORDER[base_weight]


def generate_derived_insights(
    current_wbgt: Optional[float],
    wbgt_level: str,
    mri: Optional[float],
    mri_level: str,
    rr: Optional[float],
    trend: str,
    persistence: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Generate concise, grounded data-derived insight messages."""
    insights: List[Dict[str, str]] = []

    # 1. Current Condition
    if current_wbgt is not None:
        insights.append({
            "type": "CURRENT_CONDITION",
            "priority": "HIGH" if wbgt_level in ["HIGH", "VERY_HIGH", "EXTREME"] else "MEDIUM",
            "message": f"Current outdoor WBGT is {current_wbgt:.1f}Â°C ({wbgt_level} thermal stress level)."
        })

    # 2. Epidemiological Risk Insight
    if rr is not None and rr > 1.00:
        excess_pct = (rr - 1.0) * 100
        insights.append({
            "type": "EPIDEMIOLOGICAL_RISK",
            "priority": "HIGH" if mri_level in ["HIGH", "VERY_HIGH", "EXTREME"] else "MEDIUM",
            "message": f"Modeled Relative Risk is {rr:.3f} (+{excess_pct:.1f}% excess heat-associated mortality risk relative to the 30.0Â°C reference baseline)."
        })
    elif mri is not None:
        insights.append({
            "type": "EPIDEMIOLOGICAL_RISK",
            "priority": "LOW",
            "message": f"Mortality Risk Index is currently {mri:.1f}/100 (Baseline exposure zone)."
        })

    # 3. Forecast Trend
    if trend == "RAPIDLY_INCREASING":
        insights.append({
            "type": "FORECAST_TREND",
            "priority": "HIGH",
            "message": "Heat stress is expected to intensify rapidly over the next 48 to 72 hours; preventive measures should begin prior to peak conditions."
        })
    elif trend == "INCREASING":
        insights.append({
            "type": "FORECAST_TREND",
            "priority": "MEDIUM",
            "message": "Thermal stress levels are forecast to trend upward over the 5-day horizon."
        })
    elif trend == "IMPROVING":
        insights.append({
            "type": "FORECAST_TREND",
            "priority": "LOW",
            "message": "Thermal stress is forecast to ease gradually over the coming days."
        })

    # 4. Multi-Day Persistence
    elevated_days = persistence.get("elevated_heat_days", 0)
    if elevated_days >= 2:
        insights.append({
            "type": "PERSISTENCE",
            "priority": "HIGH" if elevated_days >= 3 else "MEDIUM",
            "message": f"Elevated thermal stress is forecast to persist for {elevated_days} days across the forecast period."
        })

    # 5. Peak Timing
    peak_wbgt = persistence.get("peak_wbgt")
    peak_day = persistence.get("peak_day")
    if peak_wbgt is not None and peak_day is not None:
        insights.append({
            "type": "PEAK_WARNING",
            "priority": "HIGH" if peak_wbgt >= 31.1 else "MEDIUM",
            "message": f"Peak forecast WBGT is expected to reach {peak_wbgt:.1f}Â°C on {peak_day}."
        })

    return insights


def build_risk_context(
    current_wbgt: Optional[float],
    current_mri: Optional[float],
    current_rr: Optional[float],
    current_af: Optional[float],
    forecast_days: List[Dict[str, Any]],
    audience: str = "PUBLIC"
) -> Dict[str, Any]:
    """Construct full risk context object for downstream recommendation filtering and AI."""
    wbgt_level = get_wbgt_severity_level(current_wbgt)
    mri_level = get_mri_severity_level(current_mri)
    trend = analyze_forecast_trend(current_wbgt, forecast_days)
    persistence = analyze_heat_persistence(forecast_days)
    overall_level = synthesize_overall_heat_health_level(
        wbgt_level, mri_level, trend, persistence["elevated_heat_days"]
    )
    insights = generate_derived_insights(
        current_wbgt, wbgt_level, current_mri, mri_level, current_rr, trend, persistence
    )

    return {
        "wbgt": round(current_wbgt, 2) if current_wbgt is not None else None,
        "wbgt_level": wbgt_level,
        "mortality_risk_index": round(current_mri, 1) if current_mri is not None else None,
        "mortality_risk_level": mri_level,
        "relative_risk": round(current_rr, 4) if current_rr is not None else None,
        "attributable_fraction": round(current_af, 4) if current_af is not None else None,
        "forecast_trend": trend,
        "elevated_heat_days": persistence["elevated_heat_days"],
        "peak_wbgt": persistence["peak_wbgt"],
        "peak_day": persistence["peak_day"],
        "peak_mri": persistence["peak_mri"],
        "peak_rr": persistence["peak_rr"],
        "overall_heat_health_level": overall_level,
        "audience": audience.strip().upper(),
        "insights": insights,
    }


