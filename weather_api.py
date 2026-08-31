"""Open-Meteo ingestion and Liljegren (2008) outdoor WBGT calculations.

Heat/mass-transfer portions port Argonne's reference ``wbgt.c``. NOAA solar
position and log-profile wind adjustment are the two documented substitutions
needed for Open-Meteo data.
"""
import json
import math
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen

from health_impact import build_health_impact

DEFAULT_ENV_PATH = ".env"
CURRENT_FIELDS = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "surface_pressure", "shortwave_radiation"]
HOURLY_FIELDS = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "shortwave_radiation", "surface_pressure"]

# Liljegren / Argonne reference constants.
PI = math.pi
SOLAR_CONST, CZA_MIN, NORMSOLAR_MAX = 1367.0, 0.00873, 0.85
STEFANB, Cp, M_AIR, M_H2O, R_GAS = 5.6696e-8, 1003.5, 28.97, 18.015, 8314.34
RATIO, R_AIR = Cp * M_AIR / M_H2O, R_GAS / M_AIR
Pr = Cp / (Cp + 1.25 * R_AIR)
EMIS_WICK, ALB_WICK, D_WICK, L_WICK = 0.95, 0.4, 0.007, 0.0254
EMIS_GLOBE, ALB_GLOBE, D_GLOBE = 0.95, 0.05, 0.0508
EMIS_SFC, ALB_SFC = 0.999, 0.45
REF_HEIGHT, MIN_SPEED, CONVERGENCE, MAX_ITER = 2.0, 0.13, 0.02, 50


def load_api_url(env_path=DEFAULT_ENV_PATH):
    """Return the weather API URL stored in the .env file."""
    if not os.path.exists(env_path):
        raise FileNotFoundError(f"Environment file not found: {env_path}")
    with open(env_path, encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = (part.strip() for part in line.split("=", 1))
                if key.lower() == "api_key":
                    return value
    raise ValueError(f"No api_key entry found in {env_path}")


def parse_api_url(api_url):
    parsed = urlparse(api_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid API URL: {api_url}")
    params = parse_qs(parsed.query, keep_blank_values=True)
    return {"base_url": f"{parsed.scheme}://{parsed.netloc}{parsed.path}", **{k: v[0] if v else "" for k, v in params.items()}}


def validate_location(latitude, longitude):
    if latitude is None or longitude is None:
        raise ValueError("Both latitude and longitude are required.")
    if not -90 <= latitude <= 90:
        raise ValueError(f"Latitude out of range: {latitude}")
    if not -180 <= longitude <= 180:
        raise ValueError(f"Longitude out of range: {longitude}")


def build_weather_url(latitude, longitude, forecast_days=5):
    """Build the GMT Open-Meteo request required by the WBGT calculation."""
    validate_location(latitude, longitude)
    if forecast_days <= 0:
        raise ValueError("--days must be a positive integer.")
    params = {"latitude": latitude, "longitude": longitude,
              "current": ",".join(CURRENT_FIELDS), "hourly": ",".join(HOURLY_FIELDS),
              "timezone": "GMT", "forecast_days": int(forecast_days), "wind_speed_unit": "ms"}
    return "https://api.open-meteo.com/v1/forecast?" + urlencode(params)


def fetch_weather_snapshot(env_path=DEFAULT_ENV_PATH, latitude=None, longitude=None, forecast_days=5):
    api_url = build_weather_url(latitude, longitude, forecast_days) if latitude is not None and longitude is not None else load_api_url(env_path)
    with urlopen(api_url) as response:
        return json.loads(response.read().decode("utf-8"))


def _parse_utc(timestamp):
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).astimezone(timezone.utc)


def wind_speed_10m_to_2m(wind_speed_10m, roughness_length=0.1):
    """Log-profile 10 m→2 m conversion; a required Open-Meteo substitution.

    It is not Liljegren's stability-aware height adjustment because Open-Meteo
    does not provide its required vertical temperature gradient. Configure the
    roughness length per site when land-use data is available.
    """
    if not 0 < roughness_length < REF_HEIGHT:
        raise ValueError("roughness_length must be greater than 0 and less than 2 m")
    return max(float(wind_speed_10m) * math.log(REF_HEIGHT / roughness_length) / math.log(10 / roughness_length), MIN_SPEED)


def solar_position(timestamp, latitude, longitude, avg=60):
    """Return ``(cza, soldist)`` with NOAA solar equations.

    NOAA's fractional-year approximation substitutes for the reference C
    program's Astronomical Almanac routine. Hourly means are centered over
    ``avg`` minutes, matching the reference method.
    """
    validate_location(latitude, longitude)
    moment = _parse_utc(timestamp) - timedelta(minutes=float(avg) / 2)
    days = 366 if moment.year % 4 == 0 and (moment.year % 100 != 0 or moment.year % 400 == 0) else 365
    doy = moment.timetuple().tm_yday + (moment.hour + moment.minute / 60 + moment.second / 3600) / 24
    gamma = 2 * PI / days * (doy - 1)
    dec = (0.006918 - .399912 * math.cos(gamma) + .070257 * math.sin(gamma)
           - .006758 * math.cos(2 * gamma) + .000907 * math.sin(2 * gamma)
           - .002697 * math.cos(3 * gamma) + .00148 * math.sin(3 * gamma))
    eot = 229.18 * (.000075 + .001868 * math.cos(gamma) - .032077 * math.sin(gamma)
                    - .014615 * math.cos(2 * gamma) - .040849 * math.sin(2 * gamma))
    solar_minutes = (moment.hour * 60 + moment.minute + moment.second / 60 + eot + 4 * longitude) % 1440
    hour_angle = math.radians(solar_minutes / 4 - 180)
    lat = math.radians(latitude)
    cza = math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(hour_angle)
    # E0 is standard eccentricity correction = 1 / soldist².
    e0 = 1.00011 + .034221 * math.cos(gamma) + .00128 * math.sin(gamma) + .000719 * math.cos(2 * gamma) + .000077 * math.sin(2 * gamma)
    return cza, 1 / math.sqrt(e0)


def adjust_solar_irradiance(solar, cza, soldist):
    toasolar = SOLAR_CONST * max(0.0, cza) / soldist ** 2
    if cza < CZA_MIN:
        toasolar = 0.0
    if toasolar <= 0:
        return 0.0, 0.0
    normsolar = min(max(0.0, float(solar)) / toasolar, NORMSOLAR_MAX)
    fdir = math.exp(3 - 1.34 * normsolar - 1.65 / normsolar) if normsolar else 0.0
    return normsolar * toasolar, max(0.0, min(fdir, .9))


# Reference helper functions (all temperatures are Kelvin and pressures mb).
def esat(tk):
    return 1.004 * 6.1121 * math.exp(17.502 * ((tk - 273.15) / (tk - 32.18)))


def dew_point(e):
    z = math.log(e / (6.1121 * 1.004))
    return 273.15 + 240.97 * z / (17.502 - z)


def viscosity(tk):
    omega = ((tk / 97.0) - 2.9) / 0.4 * (-0.034) + 1.048
    return 2.6693e-6 * math.sqrt(M_AIR * tk) / (3.617 ** 2 * omega)


def thermal_cond(tk): return (Cp + 1.25 * R_AIR) * viscosity(tk)


def diffusivity(tk, pres_mb):
    return (3.64e-4 * (tk / math.sqrt(132.0 * 647.3)) ** 2.334 * (36.4 * 218.0) ** (1 / 3)
            * (132.0 * 647.3) ** (5 / 12) * math.sqrt(1 / M_AIR + 1 / M_H2O) / (pres_mb / 1013.25) * 1e-4)


def evap(tk): return (313.15 - tk) / 30 * -71100.0 + 2.4073e6
def emis_atm(tk, rh): return .575 * (rh * esat(tk)) ** .143


def h_cylinder_in_air(diameter, length, tref_k, pres_mb, speed):
    density = pres_mb * 100 / (R_AIR * tref_k)
    re = max(speed, MIN_SPEED) * density * diameter / viscosity(tref_k)
    return .281 * re ** .6 * Pr ** .44 * thermal_cond(tref_k) / diameter


def h_sphere_in_air(diameter, tref_k, pres_mb, speed):
    density = pres_mb * 100 / (R_AIR * tref_k)
    re = max(speed, MIN_SPEED) * density * diameter / viscosity(tref_k)
    return (2.0 + .6 * math.sqrt(re) * Pr ** (1 / 3)) * thermal_cond(tref_k) / diameter


def _natural_wet_bulb(tk, rh, pres, speed, solar, fdir, cza, rad=1):
    sza, eair, previous = math.acos(max(-1.0, min(1.0, cza))), rh * esat(tk), dew_point(rh * esat(tk))
    for _ in range(MAX_ITER):
        tref = .5 * (previous + tk)
        h = h_cylinder_in_air(D_WICK, L_WICK, tref, pres, speed)
        fatm = (STEFANB * EMIS_WICK * (.5 * (emis_atm(tk, rh) * tk ** 4 + EMIS_SFC * tk ** 4) - previous ** 4)
                + (1 - ALB_WICK) * solar * ((1 - fdir) * (1 + .25 * D_WICK / L_WICK) + fdir * (math.tan(sza) / PI + .25 * D_WICK / L_WICK) + ALB_SFC))
        density = pres * 100 / (R_AIR * tref)
        sc = viscosity(tref) / (density * diffusivity(tref, pres))
        current = tk - evap(tref) / RATIO * (esat(previous) - eair) / (pres - esat(previous)) * (Pr / sc) ** .56 + fatm / h * rad
        converged = abs(current - previous) < CONVERGENCE
        previous = .9 * previous + .1 * current  # reference damping, even when converged
        if converged:
            return current - 273.15
    return None


def _globe_temperature(tk, rh, pres, speed, solar, fdir, cza):
    previous = tk
    dir_term = fdir * (1 / (2 * cza) - 1) if cza > 0 else 0.0
    for _ in range(MAX_ITER):
        tref = .5 * (previous + tk)
        h = h_sphere_in_air(D_GLOBE, tref, pres, speed)
        balance = (.5 * (emis_atm(tk, rh) * tk ** 4 + EMIS_SFC * tk ** 4)
                   - h / (STEFANB * EMIS_GLOBE) * (previous - tk)
                   + solar / (2 * STEFANB * EMIS_GLOBE) * (1 - ALB_GLOBE) * (dir_term + 1 + ALB_SFC))
        if balance < 0:
            return None
        current = balance ** .25
        converged = abs(current - previous) < CONVERGENCE
        previous = .9 * previous + .1 * current
        if converged:
            return current - 273.15
    return None


def calculate_liljegren_outdoor_wbgt(temperature_c, relative_humidity, wind_speed_ms, shortwave_radiation_w_m2, surface_pressure_hpa, timestamp, latitude, longitude, avg=60, roughness_length=.1):
    """Calculate one outdoor Liljegren WBGT record from Open-Meteo inputs.

    Solvers return no result (``None``) on failure; failed values are never
    silently clamped or replaced with zero.
    """
    if surface_pressure_hpa <= 0:
        raise ValueError("surface_pressure_hpa must be positive")
    if not 0 < relative_humidity <= 100:
        raise ValueError("relative_humidity must be in (0, 100]")
    cza, soldist = solar_position(timestamp, latitude, longitude, avg)
    solar, fdir = adjust_solar_irradiance(shortwave_radiation_w_m2, cza, soldist)
    tk, rh = float(temperature_c) + 273.15, float(relative_humidity) / 100
    speed = wind_speed_10m_to_2m(wind_speed_ms, roughness_length)
    tnwb = _natural_wet_bulb(tk, rh, float(surface_pressure_hpa), speed, solar, fdir, cza)
    tglobe = _globe_temperature(tk, rh, float(surface_pressure_hpa), speed, solar, fdir, cza)
    converged = tnwb is not None and tglobe is not None
    return {"tnwb_c": tnwb, "tglobe_c": tglobe,
            "wbgt_c": .7 * tnwb + .2 * tglobe + .1 * float(temperature_c) if converged else None,
            "converged": converged}


def risk_category(wbgt_c):
    """Display flag thresholds from the supplied outdoor WBGT chart (°C)."""
    if wbgt_c is None: return None
    if wbgt_c < 27.8: return "White"
    if wbgt_c < 29.5: return "Green"
    if wbgt_c < 31.1: return "Yellow"
    if wbgt_c < 32.2: return "Red"
    return "Black"


def calculate_hourly_wbgt(data, latitude=None, longitude=None, roughness_length=.1):
    """Return every Open-Meteo hour as an output-contract WBGT record."""
    latitude = data.get("latitude") if latitude is None else latitude
    longitude = data.get("longitude") if longitude is None else longitude
    validate_location(latitude, longitude)
    hourly = data.get("hourly", {})
    output = []
    for i, timestamp in enumerate(hourly.get("time", [])):
        try:
            tair, rh = hourly["temperature_2m"][i], hourly["relative_humidity_2m"][i]
            wind, solar, pres = hourly["wind_speed_10m"][i], hourly["shortwave_radiation"][i], hourly["surface_pressure"][i]
            if not all(math.isfinite(float(value)) for value in (tair, rh, wind, solar, pres)):
                raise ValueError("Weather inputs must be finite numbers")
            result = calculate_liljegren_outdoor_wbgt(tair, rh, wind, solar, pres, timestamp, latitude, longitude, roughness_length=roughness_length)
        except (IndexError, KeyError, TypeError, ValueError):
            tair = rh = wind = solar = None
            result = {"tnwb_c": None, "tglobe_c": None, "wbgt_c": None, "converged": False}
        record = {"lat": latitude, "lon": longitude, "time": _parse_utc(timestamp).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "tair_c": tair, "rh_pct": rh, "wind_ms": wind, "solar_wm2": solar, **result}
        record["risk"] = risk_category(result["wbgt_c"])
        output.append(record)
    return output


def daily_max_wbgt(hourly_series):
    """Return peak valid WBGT record for each GMT/UTC calendar day."""
    maxima = {}
    for item in hourly_series:
        if item["wbgt_c"] is not None:
            day = item["time"][:10]
            if day not in maxima or item["wbgt_c"] > maxima[day]["wbgt_c"]:
                maxima[day] = item
    return list(maxima.values())


def calculate_current_wbgt(data, latitude=None, longitude=None, roughness_length=.1):
    """Return the latest Open-Meteo current observation in the hourly contract."""
    latitude = data.get("latitude") if latitude is None else latitude
    longitude = data.get("longitude") if longitude is None else longitude
    validate_location(latitude, longitude)
    current = data.get("current", {})
    try:
        if not all(math.isfinite(float(current[field])) for field in CURRENT_FIELDS):
            raise ValueError("Weather inputs must be finite numbers")
        result = calculate_liljegren_outdoor_wbgt(
            current["temperature_2m"], current["relative_humidity_2m"], current["wind_speed_10m"],
            current["shortwave_radiation"], current["surface_pressure"], current["time"],
            latitude, longitude, roughness_length=roughness_length,
        )
        tair, rh, wind, solar = (current["temperature_2m"], current["relative_humidity_2m"],
                                 current["wind_speed_10m"], current["shortwave_radiation"])
    except (KeyError, TypeError, ValueError):
        result = {"tnwb_c": None, "tglobe_c": None, "wbgt_c": None, "converged": False}
        tair = rh = wind = solar = None
    return {"lat": latitude, "lon": longitude, "time": _parse_utc(current.get("time", "1970-01-01T00:00")).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tair_c": tair, "rh_pct": rh, "wind_ms": wind, "solar_wm2": solar, **result,
            "risk": risk_category(result["wbgt_c"])}


def build_dashboard_payload(data, latitude=None, longitude=None, roughness_length=.1):
    """Build one API response for the live GIS dashboard."""
    hourly = calculate_hourly_wbgt(data, latitude, longitude, roughness_length)
    health_impact = build_health_impact(hourly, latitude if latitude is not None else data.get("latitude"),
                                        longitude if longitude is not None else data.get("longitude"))
    for record, ihi_record in zip(hourly, health_impact["hourly_ihi"]):
        record["ihi_c"] = ihi_record["ihi_c"]
        record["ihi_validity"] = ihi_record["validity"]
    return {"current": calculate_current_wbgt(data, latitude, longitude, roughness_length),
            "hourly": hourly, "daily_max_wbgt": daily_max_wbgt(hourly), "health_impact": health_impact}


def forecast_window_summary(data, requested_days):
    times = data.get("hourly", {}).get("time", [])
    return {"requested_days": requested_days, "forecast_hours_returned": len(times), "forecast_start": times[0] if times else None, "forecast_end": times[-1] if times else None}


def preview_window(data, limit=5):
    hourly, times = data.get("hourly", {}), data.get("hourly", {}).get("time", [])
    def sample(indexes):
        return {"time": [times[i] for i in indexes], **{field: [hourly.get(field, [None] * len(times))[i] for i in indexes] for field in HOURLY_FIELDS}}
    return {"first_5_hours": sample(range(min(limit, len(times)))), "last_5_hours": sample(range(max(0, len(times) - limit), len(times)))}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch Open-Meteo data and calculate outdoor Liljegren WBGT.")
    parser.add_argument("--lat", type=float); parser.add_argument("--lon", type=float)
    parser.add_argument("--days", type=int, default=5); parser.add_argument("--env", default=DEFAULT_ENV_PATH)
    args = parser.parse_args()
    if (args.lat is None) != (args.lon is None): parser.error("Both --lat and --lon must be provided together.")
    data = fetch_weather_snapshot(args.env, args.lat, args.lon, args.days)
    lat = args.lat if args.lat is not None else float(parse_api_url(load_api_url(args.env))["latitude"])
    lon = args.lon if args.lon is not None else float(parse_api_url(load_api_url(args.env))["longitude"])
    series = calculate_hourly_wbgt(data, lat, lon)
    print(json.dumps({"hourly_wbgt": series, "daily_max_wbgt": daily_max_wbgt(series), "forecast_summary": forecast_window_summary(data, args.days)}, indent=2))
