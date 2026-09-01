"""Dynamic Geocoding Service using Open-Meteo Geocoding API.

Enables dynamic geocoding for ANY valid city worldwide without any hardcoded
or restricted city lists.
"""

import json
import time
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

GEOCODING_API_BASE = "https://geocoding-api.open-meteo.com/v1/search"
CACHE_TTL_SECONDS = 3600  # 1 hour cache for geocoded coordinates

_geocode_cache: Dict[str, Dict[str, Any]] = {}


def geocode_city(city_name: str, cache_ttl: int = CACHE_TTL_SECONDS) -> Dict[str, Any]:
    """Resolve a city name dynamically to latitude, longitude, and metadata.

    Args:
        city_name: Name of the city (e.g. 'Pune', 'Jaipur', 'Tokyo').
        cache_ttl: In-memory cache time-to-live in seconds.

    Returns:
        Dict with keys:
            - city: Official resolved name of the city
            - latitude: Float latitude in [-90, 90]
            - longitude: Float longitude in [-180, 180]
            - country: Country name
            - country_code: 2-letter ISO country code
            - admin1: State / administrative division (or empty string)
            - timezone: Timezone string (e.g. 'Asia/Kolkata')
            - elevation: Elevation in meters (or None)
            - population: Population integer (or None)

    Raises:
        ValueError: If city_name is empty, invalid, or no match is found.
        RuntimeError: If upstream geocoding service fails or is unreachable.
    """
    if not city_name or not city_name.strip():
        raise ValueError("City name cannot be empty.")

    normalized_name = city_name.strip()
    cache_key = normalized_name.lower()

    # Check cache
    cached = _geocode_cache.get(cache_key)
    if cached and (time.time() - cached["cached_at"] < cache_ttl):
        return cached["result"]

    params = {
        "name": normalized_name,
        "count": 1,
        "language": "en",
        "format": "json"
    }
    url = f"{GEOCODING_API_BASE}?{urlencode(params)}"

    try:
        req = Request(url, headers={"User-Agent": "ExtremeHeatwaveWarningSystem/1.0"})
        with urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as err:
        raise RuntimeError(f"Geocoding service unavailable for '{city_name}': {err}")
    except json.JSONDecodeError as err:
        raise RuntimeError(f"Invalid response from geocoding service for '{city_name}': {err}")

    results = payload.get("results")
    if not results or len(results) == 0:
        raise ValueError(f"City not found: '{city_name}'. Please verify the spelling.")

    match = results[0]
    result = {
        "city": match.get("name", normalized_name),
        "latitude": round(float(match["latitude"]), 5),
        "longitude": round(float(match["longitude"]), 5),
        "country": match.get("country", ""),
        "country_code": match.get("country_code", ""),
        "admin1": match.get("admin1", ""),
        "timezone": match.get("timezone", "UTC"),
        "elevation": match.get("elevation"),
        "population": match.get("population"),
    }

    _geocode_cache[cache_key] = {
        "cached_at": time.time(),
        "result": result
    }

    return result


def clear_geocode_cache() -> None:
    """Clear the in-memory geocoding cache."""
    _geocode_cache.clear()


