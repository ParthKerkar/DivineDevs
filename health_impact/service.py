"""Health-impact indicators downstream of the existing WBGT weather pipeline.

This module does not fit an epidemiological model and never produces deaths or
admissions.  It applies only the discrete published comparisons documented in
the configuration below.
"""
import json
import math
import os
from collections import defaultdict


INDIA_BOUNDS = (6.0, 37.5, 68.0, 98.5)  # South, north, west, east; coverage guard.
ZONE_FILE = os.path.join(os.path.dirname(__file__), "data", "india_climate_zones.geojson")
MORTALITY_REFERENCE = "Choudhary RK et al. (2024), doi:10.1021/acs.est.3c05218"
HOSPITAL_REFERENCE = "Agarwal AK et al. (2018), doi:10.4103/IJOEM_IJOEM_94_17"

# Only these three entries have a direct published all-age all-cause estimate.
MORTALITY_EVIDENCE = {
    "semiarid": {"representative_city": "Delhi", "representative_zone": "Semiarid", "effects": {"very_hot": .034, "sweltering": .059}, "lag_days": 3, "coverage": "direct"},
    "humid_subtropical": {"representative_city": "Varanasi", "representative_zone": "Humid subtropical", "effects": {"very_hot": .064, "sweltering": .081}, "lag_days": 4, "coverage": "direct"},
    "tropical_wet_and_dry": {"representative_city": "Chennai", "representative_zone": "Tropical wet and dry", "effects": {"very_hot": .010, "sweltering": .080}, "lag_days": 6, "coverage": "direct"},
}
LAG_EVIDENCE_DAYS = {"Delhi": 3, "Varanasi": 4, "Chennai": 6}
# Explicit transfer configuration for zones outside the paper's mortality cities.
EXTRAPOLATED_PROXIES = {
    "arid": "semiarid", "tropical_wet": "tropical_wet_and_dry",
}
COMFORT_THRESHOLDS = {
    "arid": (22.9, 26.0, 28.8, 31.4),
    "semiarid": (23.0, 25.5, 28.0, 30.5),
    "humid_subtropical": (22.5, 25.4, 27.7, 30.2),
    "tropical_wet": (23.5, 25.1, 26.7, 28.5),
    "tropical_wet_and_dry": (23.8, 25.8, 28.1, 30.5),
}


def calculate_ihi(temperature_c, relative_humidity_pct, shortwave_radiation_w_m2, wind_speed_ms):
    """Calculate the Choudhary et al. hourly India Heat Index exactly."""
    values = (temperature_c, relative_humidity_pct, shortwave_radiation_w_m2, wind_speed_ms)
    if any(value is None for value in values):
        return None
    try:
        temperature_c, relative_humidity_pct, shortwave_radiation_w_m2, wind_speed_ms = map(float, values)
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(value) for value in (temperature_c, relative_humidity_pct, shortwave_radiation_w_m2, wind_speed_ms)):
        return None
    return (0.820 * temperature_c + 0.123 * relative_humidity_pct
            + 0.004 * shortwave_radiation_w_m2 - 0.117 * wind_speed_ms - 6.727)


def ihi_validity(temperature_c, relative_humidity_pct, shortwave_radiation_w_m2, wind_speed_ms):
    """Report whether inputs fall inside the IHI development ranges in the paper."""
    named = {"temperature_c": (temperature_c, 20.0, 49.5), "relative_humidity_percent": (relative_humidity_pct, 10.0, 100.0),
             "shortwave_radiation_w_m2": (shortwave_radiation_w_m2, 0.0, 1050.0), "wind_speed_ms": (wind_speed_ms, 0.1, 20.0)}
    warnings = []
    for name, (value, low, high) in named.items():
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            warnings.append(f"Missing or invalid {name}; IHI was not calculated.")
            continue
        if not math.isfinite(numeric):
            warnings.append(f"Non-finite {name}; IHI was not calculated.")
        elif not low <= numeric <= high:
            warnings.append(f"{name}={numeric} is outside the published IHI range {low}–{high}.")
    return {"within_published_range": not warnings, "warnings": warnings}


def _inside_ring(longitude, latitude, ring):
    """Boundary-inclusive ray-casting point-in-polygon test for lon/lat rings."""
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if min(y1, y2) <= latitude <= max(y1, y2) and min(x1, x2) <= longitude <= max(x1, x2):
            cross = (x2 - x1) * (latitude - y1) - (y2 - y1) * (longitude - x1)
            if abs(cross) < 1e-10:
                return True
        if (y1 > latitude) != (y2 > latitude):
            intersection = (x2 - x1) * (latitude - y1) / (y2 - y1) + x1
            if longitude < intersection:
                inside = not inside
    return inside


def _load_zone_features(zone_file=ZONE_FILE):
    with open(zone_file, encoding="utf-8") as source:
        return json.load(source)["features"]


def classify_climate_zone(latitude, longitude, zone_file=ZONE_FILE):
    """Return an assigned zone through local GIS point-in-polygon lookup."""
    south, north, west, east = INDIA_BOUNDS
    if not south <= float(latitude) <= north or not west <= float(longitude) <= east:
        raise ValueError("Health-impact coverage is limited to India coordinates.")
    for feature in _load_zone_features(zone_file):
        geometry = feature["geometry"]
        polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        if any(_inside_ring(float(longitude), float(latitude), polygon[0]) for polygon in polygons):
            return feature["properties"]["zone"]
    raise ValueError("Climate-zone assignment failed for this Indian coordinate; no zone is guessed.")


def ihi_comfort_class(ihi, climate_zone):
    """Assign the published class; Mountainous remains deliberately unsupported."""
    if ihi is None:
        return None
    thresholds = COMFORT_THRESHOLDS.get(climate_zone)
    if thresholds is None:
        return "unsupported"
    for label, threshold in zip(("comfortable", "warm", "hot", "very_hot"), thresholds):
        if ihi <= threshold:
            return label
    return "sweltering"


def _run_length(items):
    longest = current = 0
    for item in items:
        current = current + 1 if item else 0
        longest = max(longest, current)
    return longest


def _daily_weather(hourly):
    days = defaultdict(list)
    for record in hourly:
        if record.get("time"):
            days[record["time"][:10]].append(record)
    result = []
    for day, records in sorted(days.items()):
        ihis = [record.get("ihi") for record in records if record.get("ihi") is not None]
        temperatures = [record.get("tair_c") for record in records if record.get("tair_c") is not None]
        result.append({"date": day, "daily_max_ihi": max(ihis) if ihis else None,
                       "daily_mean_ihi": sum(ihis) / len(ihis) if ihis else None,
                       "tmax": max(temperatures) if temperatures else None})
    return result


def build_health_impact(hourly, latitude, longitude, days=5):
    """Build the 5-day evidence-based mortality and hospital stress response."""
    zone = classify_climate_zone(latitude, longitude)
    annotated_hourly = []
    for record in hourly:
        item = dict(record)
        validity = ihi_validity(item.get("tair_c"), item.get("rh_pct"), item.get("solar_wm2"), item.get("wind_ms"))
        item["ihi"] = (calculate_ihi(item.get("tair_c"), item.get("rh_pct"), item.get("solar_wm2"), item.get("wind_ms"))
                       if validity["within_published_range"] else None)
        item["ihi_validity"] = validity
        annotated_hourly.append(item)
    daily = _daily_weather(annotated_hourly)
    # The first calendar date is D0; API callers request 6 days to yield D+1…D+5.
    forecast_days = daily[1:days + 1] if len(daily) > 1 else []
    evidence_zone = zone if zone in MORTALITY_EVIDENCE else EXTRAPOLATED_PROXIES.get(zone)
    evidence = MORTALITY_EVIDENCE.get(evidence_zone)
    coverage = "direct" if zone in MORTALITY_EVIDENCE else "extrapolated" if evidence else "unsupported"
    mortality_forecast, hospitalization_forecast = [], []
    for item in forecast_days:
        classification = ihi_comfort_class(item["daily_max_ihi"], zone)
        published_effect = evidence["effects"].get(classification) if evidence and classification else None
        effect_available = published_effect is not None
        # The paper states these are effects *per unit increase in IHI*.  A
        # day-specific RR would require the unavailable fitted response curve
        # and reference IHI, so it is intentionally not derived here.
        unit_rr = 1 + published_effect if effect_available else None
        explanation = ("Published class-specific mortality effect per 1°C IHI increase; not a day-specific death prediction."
                       if effect_available else "No exact published mortality effect is available for this IHI class/zone; no RR was inferred.")
        mortality_forecast.append({"date": item["date"], "daily_max_ihi": item["daily_max_ihi"],
            "daily_mean_ihi": item["daily_mean_ihi"], "climate_zone": zone, "ihi_class": classification,
            "mortality_effect_available": effect_available, "mortality_effect_percent_per_ihi_c": round(100 * published_effect, 1) if effect_available else None,
            "relative_risk_per_ihi_c": unit_rr, "mortality_index_per_ihi_c": round(100 * unit_rr, 1) if unit_rr else None,
            "mortality_rr": None, "mortality_index": None, "mortality_level": "Elevated" if effect_available else "Unavailable",
            "risk_basis": "published per-unit IHI effect" if effect_available else "no published class-specific effect applied",
            "is_sweltering": classification == "sweltering", "epidemiology_coverage": coverage,
            "representative_city": evidence["representative_city"] if evidence else None,
            "representative_zone": evidence["representative_zone"] if evidence else None,
            "is_extrapolated": coverage == "extrapolated", "explanation": explanation})
        # Table 1 is the explicit comparison: >=39°C vs <38°C.  The narrative
        # also says >=40°C; retain that conflict in metadata rather than hide it.
        spike = item["tmax"] is not None and item["tmax"] >= 39.0
        hospitalization_forecast.append({"date": item["date"], "tmax": item["tmax"],
            "tmax_c": item["tmax"], "hospitalization_effect_available": spike,
            "hospitalization_spike": spike, "hospitalization_rr": 1.186 if spike else None,
            "hospitalization_stress_index": 118.6 if spike else None,
            "hospitalization_effect_percent": 18.6 if spike else None,
            "hospitalization_level": "Elevated / study comparison" if spike else "Unavailable",
            "risk_basis": "Agarwal Table 1: >=39°C vs <38°C" if spike else "outside the exact published comparison; no continuous effect inferred",
            "explanation": "Single Gwalior tertiary-hospital comparison, not a national hospitalization model."})
    sweltering = [item["is_sweltering"] for item in mortality_forecast]
    spikes = [item["hospitalization_spike"] for item in hospitalization_forecast]
    return {"hourly_ihi": [{"time": item.get("time"), "ihi_c": item["ihi"], "validity": item["ihi_validity"]} for item in annotated_hourly],
        "mortality": {"reference": MORTALITY_REFERENCE, "climate_zone": zone,
            "representative_city": evidence["representative_city"] if evidence else None,
            "representative_zone": evidence["representative_zone"] if evidence else None,
            "coverage": coverage, "is_extrapolated": coverage == "extrapolated", "forecast": mortality_forecast,
            "lag_evidence_days": evidence["lag_days"] if evidence else None,
            "lag_evidence": LAG_EVIDENCE_DAYS,
            "lag_evidence_window": "3–6 days", "sweltering_days_next_5": sum(sweltering),
            "max_ihi_next_5": max((item["daily_max_ihi"] for item in mortality_forecast if item["daily_max_ihi"] is not None), default=None),
            "longest_sweltering_run": _run_length(sweltering)},
        "hospitalization": {"reference": HOSPITAL_REFERENCE, "reference_rr": 1.186,
            "forecast": hospitalization_forecast, "spike_days_next_5": sum(spikes),
            "number_of_spike_days": sum(spikes),
            "longest_spike_run": _run_length(spikes),
            "first_predicted_spike_day": next((item["date"] for item in hospitalization_forecast if item["hospitalization_spike"]), None),
            "maximum_5_day_hospitalization_stress": max((item["hospitalization_stress_index"] for item in hospitalization_forecast if item["hospitalization_stress_index"] is not None), default=None),
            "vulnerability_score": None}}
