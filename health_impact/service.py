"""Health-impact indicators downstream of the existing WBGT weather pipeline.

This module does not fit an epidemiological model and never produces deaths or
admissions.  It applies only the discrete published comparisons documented in
the configuration below.
"""
import json
import os
from collections import defaultdict
from datetime import date


INDIA_BOUNDS = (6.0, 37.5, 68.0, 98.5)  # South, north, west, east; coverage guard.
ZONE_FILE = os.path.join(os.path.dirname(__file__), "data", "india_climate_zones.geojson")
MORTALITY_REFERENCE = "Choudhary RK et al. (2024), doi:10.1021/acs.est.3c05218"
HOSPITAL_REFERENCE = "Agarwal AK et al. (2018), doi:10.4103/IJOEM_IJOEM_94_17"

# Only these three entries have a direct published all-age all-cause estimate.
MORTALITY_EVIDENCE = {
    "semiarid": {"representative_city": "Delhi", "representative_zone": "Semiarid", "rr": 1.059, "lag_days": 3, "coverage": "direct"},
    "humid_subtropical": {"representative_city": "Varanasi", "representative_zone": "Humid subtropical", "rr": 1.081, "lag_days": 4, "coverage": "direct"},
    "tropical_wet_and_dry": {"representative_city": "Chennai", "representative_zone": "Tropical wet and dry", "rr": 1.080, "lag_days": 6, "coverage": "direct"},
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
    return (0.820 * float(temperature_c) + 0.123 * float(relative_humidity_pct)
            + 0.004 * float(shortwave_radiation_w_m2) - 0.117 * float(wind_speed_ms) - 6.727)


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
        item["ihi"] = calculate_ihi(item.get("tair_c"), item.get("rh_pct"), item.get("solar_wm2"), item.get("wind_ms"))
        annotated_hourly.append(item)
    daily = _daily_weather(annotated_hourly)
    # The first calendar date is D0; API callers request 6 days to yield D+1…D+5.
    forecast_days = daily[1:days + 1] if len(daily) > 1 else []
    evidence_zone = zone if zone in MORTALITY_EVIDENCE else EXTRAPOLATED_PROXIES.get(zone)
    evidence = MORTALITY_EVIDENCE.get(evidence_zone)
    coverage = "direct" if zone in MORTALITY_EVIDENCE else "extrapolated"
    mortality_forecast, hospitalization_forecast = [], []
    for item in forecast_days:
        classification = ihi_comfort_class(item["daily_max_ihi"], zone)
        is_sweltering = classification == "sweltering"
        rr = evidence["rr"] if is_sweltering and evidence else 1.0
        basis = ("published sweltering-versus-comfortable comparison" if is_sweltering and evidence
                 else "reference baseline; no published category-specific RR applied")
        mortality_forecast.append({"date": item["date"], "daily_max_ihi": item["daily_max_ihi"],
            "daily_mean_ihi": item["daily_mean_ihi"], "climate_zone": zone, "ihi_class": classification,
            "mortality_rr": rr, "mortality_index": 100 * rr, "risk_basis": basis,
            "is_sweltering": is_sweltering, "epidemiology_coverage": coverage,
            "representative_city": evidence["representative_city"] if evidence else None,
            "representative_zone": evidence["representative_zone"] if evidence else None,
            "is_extrapolated": coverage == "extrapolated"})
        spike = item["tmax"] is not None and item["tmax"] >= 40.0
        hospitalization_forecast.append({"date": item["date"], "tmax": item["tmax"],
            "hospitalization_spike": spike, "hospitalization_rr": 1.186 if spike else 1.0,
            "hospitalization_stress_index": 118.6 if spike else 100.0,
            "risk_basis": "published >=40°C comparison" if spike else "reference baseline below 40°C; no continuous RR applied"})
    sweltering = [item["is_sweltering"] for item in mortality_forecast]
    spikes = [item["hospitalization_spike"] for item in hospitalization_forecast]
    return {"hourly_ihi": [{"time": item.get("time"), "ihi": item["ihi"]} for item in annotated_hourly],
        "mortality": {"reference": MORTALITY_REFERENCE, "climate_zone": zone,
            "representative_city": evidence["representative_city"] if evidence else None,
            "representative_zone": evidence["representative_zone"] if evidence else None,
            "coverage": coverage, "is_extrapolated": coverage == "extrapolated", "forecast": mortality_forecast,
            "lag_evidence_days": evidence["lag_days"] if evidence else None,
            "lag_evidence": LAG_EVIDENCE_DAYS,
            "sweltering_days_next_5": sum(sweltering),
            "max_ihi_next_5": max((item["daily_max_ihi"] for item in mortality_forecast if item["daily_max_ihi"] is not None), default=None),
            "longest_sweltering_run": _run_length(sweltering)},
        "hospitalization": {"reference": HOSPITAL_REFERENCE, "reference_rr": 1.186,
            "forecast": hospitalization_forecast, "spike_days_next_5": sum(spikes),
            "number_of_spike_days": sum(spikes),
            "longest_spike_run": _run_length(spikes),
            "first_predicted_spike_day": next((item["date"] for item in hospitalization_forecast if item["hospitalization_spike"]), None),
            "maximum_5_day_hospitalization_stress": max((item["hospitalization_stress_index"] for item in hospitalization_forecast), default=None),
            "vulnerability_score": None}}
