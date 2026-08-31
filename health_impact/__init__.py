"""Evidence-based, forecast-only heat-health indicators for India."""

from .service import build_health_impact, classify_climate_zone, calculate_ihi

__all__ = ["build_health_impact", "classify_climate_zone", "calculate_ihi"]
