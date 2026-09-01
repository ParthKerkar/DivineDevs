"""HTTP REST API Server for Extreme Heatwave Early Warning & Recommendation System.

Serves the live WBGT GIS dashboard (frontend) and provides all API endpoints.

Endpoints:
----------
- GET /api/wbgt-grid                  -> India-wide WBGT grid for the map
- GET /api/wbgt?lat=<lat>&lon=<lon>   -> WBGT + mortality risk for one point
- GET /api/search?q=<query>           -> Indian city geocoding search
- GET /api/heat-risk?city=<city>      -> Full heat risk for a city
- GET /api/recommendations            -> Evidence-guided heat health guidance
- GET /api/health                     -> Health check

Run:
----
python dashboard_server.py
"""

import json
import os
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen

from geocoding import geocode_city
from recommendation_engine import (
    get_heat_health_recommendations,
    get_heat_health_recommendations_for_coords,
    get_heat_health_recommendations_for_risk_payload,
)
from weather_api import (
    CURRENT_FIELDS,
    build_dashboard_payload,
    calculate_current_wbgt,
    fetch_heat_risk_for_city,
    fetch_heat_risk_for_coordinates,
    fetch_weather_snapshot,
    validate_location,
)

# -- Static files --------------------------------------------------------------
STATIC_DIRECTORY = os.path.join(os.path.dirname(__file__), "dashboard")

# -- Cache --------------------------------------------------------------------
CACHE_SECONDS = 300
_dashboard_cache: Dict[Tuple[float, float], Dict[str, Any]] = {}
_heat_risk_cache: Dict[str, Dict[str, Any]] = {}
_cache: Dict = {}

# -- India boundary -----------------------------------------------------------
BOUNDARY_PATH = os.path.join(STATIC_DIRECTORY, "india-boundary.geojson")


def india_polygons():
    with open(BOUNDARY_PATH, encoding="utf-8") as source:
        feature = json.load(source)["features"][0]
    geometry = feature["geometry"]
    return geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]


INDIA_POLYGONS = india_polygons()


def point_in_ring(lon, lat, ring):
    inside = False
    for index, (x1, y1) in enumerate(ring):
        x2, y2 = ring[(index + 1) % len(ring)]
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def point_in_india(lon, lat):
    for polygon in INDIA_POLYGONS:
        if point_in_ring(lon, lat, polygon[0]) and not any(
            point_in_ring(lon, lat, hole) for hole in polygon[1:]
        ):
            return True
    return False


def frange(start, stop, step):
    while start <= stop:
        yield start
        start += step


def spatial_grid_points(step=2.0):
    return [
        (round(lat, 3), round(lon, 3))
        for lat in frange(8, 35, step)
        for lon in frange(68, 97, step)
        if point_in_india(lon, lat)
    ]


# -- City data ----------------------------------------------------------------
CITY_ALIASES = {
    "bangalore": "Bengaluru", "bengalooru": "Bengaluru", "bombay": "Mumbai",
    "calcutta": "Kolkata", "madras": "Chennai", "cochin": "Kochi",
    "trivandrum": "Thiruvananthapuram", "poona": "Pune", "gurgaon": "Gurugram",
    "allahabad": "Prayagraj", "baroda": "Vadodara", "benares": "Varanasi",
    "banaras": "Varanasi", "kashi": "Varanasi", "mysore": "Mysuru",
    "simla": "Shimla", "gauhati": "Guwahati", "trichy": "Tiruchirappalli",
    "vizag": "Visakhapatnam", "calicut": "Kozhikode", "belgaum": "Belagavi",
    "hubli": "Hubballi", "mangalore": "Mangaluru", "goa": "Panaji",
    "orissa": "Bhubaneswar", "pondicherry": "Puducherry",
}

PREDEFINED_INDIAN_CITIES = [
    {"name": "Mumbai", "admin1": "Maharashtra", "lat": 19.0760, "lon": 72.8777, "country": "India"},
    {"name": "Delhi", "admin1": "Delhi", "lat": 28.6139, "lon": 77.2090, "country": "India"},
    {"name": "Bengaluru", "admin1": "Karnataka", "lat": 12.9716, "lon": 77.5946, "country": "India"},
    {"name": "Hyderabad", "admin1": "Telangana", "lat": 17.3850, "lon": 78.4867, "country": "India"},
    {"name": "Chennai", "admin1": "Tamil Nadu", "lat": 13.0827, "lon": 80.2707, "country": "India"},
    {"name": "Kolkata", "admin1": "West Bengal", "lat": 22.5726, "lon": 88.3639, "country": "India"},
    {"name": "Pune", "admin1": "Maharashtra", "lat": 18.5204, "lon": 73.8567, "country": "India"},
    {"name": "Ahmedabad", "admin1": "Gujarat", "lat": 23.0225, "lon": 72.5714, "country": "India"},
    {"name": "Jaipur", "admin1": "Rajasthan", "lat": 26.9124, "lon": 75.7873, "country": "India"},
    {"name": "Surat", "admin1": "Gujarat", "lat": 21.1702, "lon": 72.8311, "country": "India"},
    {"name": "Lucknow", "admin1": "Uttar Pradesh", "lat": 26.8467, "lon": 80.9462, "country": "India"},
    {"name": "Kanpur", "admin1": "Uttar Pradesh", "lat": 26.4499, "lon": 80.3319, "country": "India"},
    {"name": "Nagpur", "admin1": "Maharashtra", "lat": 21.1458, "lon": 79.0882, "country": "India"},
    {"name": "Indore", "admin1": "Madhya Pradesh", "lat": 22.7196, "lon": 75.8577, "country": "India"},
    {"name": "Thane", "admin1": "Maharashtra", "lat": 19.2183, "lon": 72.9781, "country": "India"},
    {"name": "Bhopal", "admin1": "Madhya Pradesh", "lat": 23.2599, "lon": 77.4126, "country": "India"},
    {"name": "Visakhapatnam", "admin1": "Andhra Pradesh", "lat": 17.6868, "lon": 83.2185, "country": "India"},
    {"name": "Patna", "admin1": "Bihar", "lat": 25.5941, "lon": 85.1376, "country": "India"},
    {"name": "Vadodara", "admin1": "Gujarat", "lat": 22.3072, "lon": 73.1812, "country": "India"},
    {"name": "Ghaziabad", "admin1": "Uttar Pradesh", "lat": 28.6692, "lon": 77.4538, "country": "India"},
    {"name": "Ludhiana", "admin1": "Punjab", "lat": 30.9010, "lon": 75.8573, "country": "India"},
    {"name": "Agra", "admin1": "Uttar Pradesh", "lat": 27.1767, "lon": 78.0081, "country": "India"},
    {"name": "Nashik", "admin1": "Maharashtra", "lat": 19.9975, "lon": 73.7898, "country": "India"},
    {"name": "Faridabad", "admin1": "Haryana", "lat": 28.4089, "lon": 77.3178, "country": "India"},
    {"name": "Meerut", "admin1": "Uttar Pradesh", "lat": 28.9845, "lon": 77.7064, "country": "India"},
    {"name": "Rajkot", "admin1": "Gujarat", "lat": 22.3039, "lon": 70.8022, "country": "India"},
    {"name": "Varanasi", "admin1": "Uttar Pradesh", "lat": 25.3176, "lon": 82.9739, "country": "India"},
    {"name": "Srinagar", "admin1": "Jammu and Kashmir", "lat": 34.0837, "lon": 74.7973, "country": "India"},
    {"name": "Aurangabad", "admin1": "Maharashtra", "lat": 19.8762, "lon": 75.3433, "country": "India"},
    {"name": "Dhanbad", "admin1": "Jharkhand", "lat": 23.7957, "lon": 86.4304, "country": "India"},
    {"name": "Amritsar", "admin1": "Punjab", "lat": 31.6340, "lon": 74.8723, "country": "India"},
    {"name": "Navi Mumbai", "admin1": "Maharashtra", "lat": 19.0330, "lon": 73.0297, "country": "India"},
    {"name": "Prayagraj", "admin1": "Uttar Pradesh", "lat": 25.4358, "lon": 81.8463, "country": "India"},
    {"name": "Ranchi", "admin1": "Jharkhand", "lat": 23.3441, "lon": 85.3096, "country": "India"},
    {"name": "Howrah", "admin1": "West Bengal", "lat": 22.5958, "lon": 88.2636, "country": "India"},
    {"name": "Coimbatore", "admin1": "Tamil Nadu", "lat": 11.0168, "lon": 76.9558, "country": "India"},
    {"name": "Jabalpur", "admin1": "Madhya Pradesh", "lat": 23.1815, "lon": 79.9864, "country": "India"},
    {"name": "Gwalior", "admin1": "Madhya Pradesh", "lat": 26.2183, "lon": 78.1828, "country": "India"},
    {"name": "Vijayawada", "admin1": "Andhra Pradesh", "lat": 16.5062, "lon": 80.6480, "country": "India"},
    {"name": "Jodhpur", "admin1": "Rajasthan", "lat": 26.2389, "lon": 73.0243, "country": "India"},
    {"name": "Madurai", "admin1": "Tamil Nadu", "lat": 9.9252, "lon": 78.1198, "country": "India"},
    {"name": "Raipur", "admin1": "Chhattisgarh", "lat": 21.2514, "lon": 81.6296, "country": "India"},
    {"name": "Kota", "admin1": "Rajasthan", "lat": 25.2138, "lon": 75.8648, "country": "India"},
    {"name": "Guwahati", "admin1": "Assam", "lat": 26.1445, "lon": 91.7362, "country": "India"},
    {"name": "Chandigarh", "admin1": "Chandigarh", "lat": 30.7333, "lon": 76.7794, "country": "India"},
    {"name": "Solapur", "admin1": "Maharashtra", "lat": 17.6599, "lon": 75.9064, "country": "India"},
    {"name": "Hubballi", "admin1": "Karnataka", "lat": 15.3647, "lon": 75.1240, "country": "India"},
    {"name": "Bareilly", "admin1": "Uttar Pradesh", "lat": 28.3670, "lon": 79.4304, "country": "India"},
    {"name": "Mysuru", "admin1": "Karnataka", "lat": 12.2958, "lon": 76.6394, "country": "India"},
    {"name": "Tiruchirappalli", "admin1": "Tamil Nadu", "lat": 10.7905, "lon": 78.7047, "country": "India"},
    {"name": "Aligarh", "admin1": "Uttar Pradesh", "lat": 27.8974, "lon": 78.0880, "country": "India"},
    {"name": "Bhubaneswar", "admin1": "Odisha", "lat": 20.2961, "lon": 85.8245, "country": "India"},
    {"name": "Salem", "admin1": "Tamil Nadu", "lat": 11.6643, "lon": 78.1460, "country": "India"},
    {"name": "Kochi", "admin1": "Kerala", "lat": 9.9312, "lon": 76.2673, "country": "India"},
    {"name": "Thiruvananthapuram", "admin1": "Kerala", "lat": 8.5241, "lon": 76.9366, "country": "India"},
    {"name": "Dehradun", "admin1": "Uttarakhand", "lat": 30.3165, "lon": 78.0322, "country": "India"},
    {"name": "Noida", "admin1": "Uttar Pradesh", "lat": 28.5355, "lon": 77.3910, "country": "India"},
    {"name": "Gurugram", "admin1": "Haryana", "lat": 28.4595, "lon": 77.0266, "country": "India"},
    {"name": "Shimla", "admin1": "Himachal Pradesh", "lat": 31.1048, "lon": 77.1734, "country": "India"},
    {"name": "Panaji", "admin1": "Goa", "lat": 15.4909, "lon": 73.8278, "country": "India"},
    {"name": "Puducherry", "admin1": "Puducherry", "lat": 11.9416, "lon": 79.8083, "country": "India"},
    {"name": "Mangaluru", "admin1": "Karnataka", "lat": 12.9141, "lon": 74.8560, "country": "India"},
    {"name": "Kozhikode", "admin1": "Kerala", "lat": 11.2588, "lon": 75.7804, "country": "India"},
    {"name": "Udaipur", "admin1": "Rajasthan", "lat": 24.5854, "lon": 73.7125, "country": "India"},
    {"name": "Jamshedpur", "admin1": "Jharkhand", "lat": 22.8046, "lon": 86.2029, "country": "India"},
    {"name": "Kolhapur", "admin1": "Maharashtra", "lat": 16.7050, "lon": 74.2433, "country": "India"},
    {"name": "Belagavi", "admin1": "Karnataka", "lat": 15.8497, "lon": 74.4977, "country": "India"},
    {"name": "Jamnagar", "admin1": "Gujarat", "lat": 22.4707, "lon": 70.0577, "country": "India"},
    {"name": "Ujjain", "admin1": "Madhya Pradesh", "lat": 23.1765, "lon": 75.7885, "country": "India"},
    {"name": "Nellore", "admin1": "Andhra Pradesh", "lat": 14.4426, "lon": 79.9865, "country": "India"},
    {"name": "Kurnool", "admin1": "Andhra Pradesh", "lat": 15.8281, "lon": 78.0373, "country": "India"},
    {"name": "Manali", "admin1": "Himachal Pradesh", "lat": 32.2432, "lon": 77.1892, "country": "India"},
    {"name": "Dharamshala", "admin1": "Himachal Pradesh", "lat": 32.2190, "lon": 76.3234, "country": "India"},
    {"name": "Rishikesh", "admin1": "Uttarakhand", "lat": 30.0869, "lon": 78.2676, "country": "India"},
    {"name": "Haridwar", "admin1": "Uttarakhand", "lat": 29.9457, "lon": 78.1642, "country": "India"},
    {"name": "Nainital", "admin1": "Uttarakhand", "lat": 29.3919, "lon": 79.4542, "country": "India"},
    {"name": "Ooty", "admin1": "Tamil Nadu", "lat": 11.4102, "lon": 76.6950, "country": "India"},
    {"name": "Kodaikanal", "admin1": "Tamil Nadu", "lat": 10.2381, "lon": 77.4892, "country": "India"},
    {"name": "Munnar", "admin1": "Kerala", "lat": 10.0889, "lon": 77.0595, "country": "India"},
    {"name": "Wayanad", "admin1": "Kerala", "lat": 11.6854, "lon": 76.1320, "country": "India"},
    {"name": "Alappuzha", "admin1": "Kerala", "lat": 9.4981, "lon": 76.3388, "country": "India"},
    {"name": "Darjeeling", "admin1": "West Bengal", "lat": 27.0410, "lon": 88.2663, "country": "India"},
    {"name": "Gangtok", "admin1": "Sikkim", "lat": 27.3389, "lon": 88.6065, "country": "India"},
    {"name": "Shillong", "admin1": "Meghalaya", "lat": 25.5788, "lon": 91.8933, "country": "India"},
    {"name": "Imphal", "admin1": "Manipur", "lat": 24.8170, "lon": 93.9368, "country": "India"},
    {"name": "Aizawl", "admin1": "Mizoram", "lat": 23.7271, "lon": 92.7176, "country": "India"},
    {"name": "Kohima", "admin1": "Nagaland", "lat": 25.6751, "lon": 94.1086, "country": "India"},
    {"name": "Agartala", "admin1": "Tripura", "lat": 23.8315, "lon": 91.2868, "country": "India"},
    {"name": "Itanagar", "admin1": "Arunachal Pradesh", "lat": 27.0844, "lon": 93.6053, "country": "India"},
    {"name": "Leh", "admin1": "Ladakh", "lat": 34.1526, "lon": 77.5771, "country": "India"},
    {"name": "Jammu", "admin1": "Jammu and Kashmir", "lat": 32.7266, "lon": 74.8570, "country": "India"},
    {"name": "Port Blair", "admin1": "Andaman and Nicobar Islands", "lat": 11.6234, "lon": 92.7265, "country": "India"},
    {"name": "Gaya", "admin1": "Bihar", "lat": 24.7914, "lon": 85.0002, "country": "India"},
    {"name": "Muzaffarpur", "admin1": "Bihar", "lat": 26.1209, "lon": 85.3647, "country": "India"},
    {"name": "Gorakhpur", "admin1": "Uttar Pradesh", "lat": 26.7606, "lon": 83.3732, "country": "India"},
    {"name": "Jhansi", "admin1": "Uttar Pradesh", "lat": 25.4484, "lon": 78.5685, "country": "India"},
    {"name": "Mathura", "admin1": "Uttar Pradesh", "lat": 27.4924, "lon": 77.6737, "country": "India"},
    {"name": "Ayodhya", "admin1": "Uttar Pradesh", "lat": 26.7922, "lon": 82.1998, "country": "India"},
    {"name": "Siliguri", "admin1": "West Bengal", "lat": 26.7271, "lon": 88.3953, "country": "India"},
    {"name": "Asansol", "admin1": "West Bengal", "lat": 23.6739, "lon": 86.9524, "country": "India"},
    {"name": "Durgapur", "admin1": "West Bengal", "lat": 23.5204, "lon": 87.3119, "country": "India"},
    {"name": "Warangal", "admin1": "Telangana", "lat": 17.9689, "lon": 79.5941, "country": "India"},
    {"name": "Nizamabad", "admin1": "Telangana", "lat": 18.6725, "lon": 78.0941, "country": "India"},
    {"name": "Karimnagar", "admin1": "Telangana", "lat": 18.4386, "lon": 79.1288, "country": "India"},
    {"name": "Khammam", "admin1": "Telangana", "lat": 17.2473, "lon": 80.1514, "country": "India"},
    {"name": "Tiruppur", "admin1": "Tamil Nadu", "lat": 11.1085, "lon": 77.3411, "country": "India"},
    {"name": "Erode", "admin1": "Tamil Nadu", "lat": 11.3410, "lon": 77.7172, "country": "India"},
    {"name": "Vellore", "admin1": "Tamil Nadu", "lat": 12.9165, "lon": 79.1325, "country": "India"},
    {"name": "Tirunelveli", "admin1": "Tamil Nadu", "lat": 8.7139, "lon": 77.7567, "country": "India"},
    {"name": "Thanjavur", "admin1": "Tamil Nadu", "lat": 10.7870, "lon": 79.1378, "country": "India"},
    {"name": "Kanyakumari", "admin1": "Tamil Nadu", "lat": 8.0883, "lon": 77.5385, "country": "India"},
    {"name": "Rameswaram", "admin1": "Tamil Nadu", "lat": 9.2876, "lon": 79.3129, "country": "India"},
    {"name": "Ajmer", "admin1": "Rajasthan", "lat": 26.4499, "lon": 74.6399, "country": "India"},
    {"name": "Bikaner", "admin1": "Rajasthan", "lat": 28.0229, "lon": 73.3119, "country": "India"},
    {"name": "Alwar", "admin1": "Rajasthan", "lat": 27.5530, "lon": 76.6346, "country": "India"},
    {"name": "Jaisalmer", "admin1": "Rajasthan", "lat": 26.9157, "lon": 70.9083, "country": "India"},
]


def geocode_city_list(query: str):
    """Search for Indian cities matching query. Returns a list of city dicts."""
    query_clean = query.strip()
    q_lower = query_clean.lower()
    search_terms = [query_clean]
    if q_lower in CITY_ALIASES and CITY_ALIASES[q_lower].lower() != q_lower:
        search_terms.append(CITY_ALIASES[q_lower])

    seen = set()
    results = []

    for city in PREDEFINED_INDIAN_CITIES:
        c_name = city["name"].lower()
        if (q_lower == c_name or q_lower in c_name or c_name.startswith(q_lower)
                or any(t.lower() in c_name for t in search_terms)):
            key = (round(city["lat"], 2), round(city["lon"], 2))
            if key not in seen:
                seen.add(key)
                results.append(dict(city))

    for term in search_terms:
        try:
            url = ("https://geocoding-api.open-meteo.com/v1/search?"
                   + urlencode({"name": term, "count": 40, "language": "en", "format": "json"}))
            with urlopen(url, timeout=8) as response:
                remote = json.loads(response.read().decode("utf-8")).get("results", [])
            for item in remote:
                lat, lon = item.get("latitude"), item.get("longitude")
                if lat is None or lon is None:
                    continue
                if item.get("country_code") == "IN" or point_in_india(lon, lat):
                    key = (round(lat, 2), round(lon, 2))
                    if key not in seen:
                        seen.add(key)
                        results.append({
                            "name": item["name"],
                            "admin1": item.get("admin1", ""),
                            "country": item.get("country", "India"),
                            "lat": lat,
                            "lon": lon,
                        })
        except Exception:
            pass

    return results


def dashboard_grid():
    key = "india-grid"
    cached = _cache.get(key)
    if cached and time.time() - cached["created"] < CACHE_SECONDS:
        return cached["payload"]

    points = spatial_grid_points()
    params = {
        "latitude": ",".join(str(p[0]) for p in points),
        "longitude": ",".join(str(p[1]) for p in points),
        "current": ",".join(CURRENT_FIELDS),
        "timezone": "GMT",
        "wind_speed_unit": "ms",
    }
    with urlopen(
        "https://api.open-meteo.com/v1/forecast?" + urlencode(params), timeout=25
    ) as response:
        snapshots = json.loads(response.read().decode("utf-8"))

    if not isinstance(snapshots, list):
        snapshots = [snapshots]

    observations = []
    for requested, snapshot in zip(points, snapshots):
        lat = snapshot.get("latitude", requested[0])
        lon = snapshot.get("longitude", requested[1])
        current = calculate_current_wbgt(snapshot, lat, lon)
        if current["wbgt_c"] is not None:
            observations.append({
                "lat": lat, "lon": lon,
                "wbgt_c": current["wbgt_c"],
                "risk": current["risk"],
            })

    payload = {
        "points": observations,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _cache[key] = {"created": time.time(), "payload": payload}
    return payload


def get_cached_dashboard(latitude: float, longitude: float) -> Dict[str, Any]:
    key = (round(latitude, 4), round(longitude, 4))
    cached = _dashboard_cache.get(key)
    if cached and (time.time() - cached["created"] < CACHE_SECONDS):
        return cached["payload"]
    payload = build_dashboard_payload(
        fetch_weather_snapshot(latitude=latitude, longitude=longitude),
        latitude, longitude,
    )
    # Drive the health panel from the exact WBGT series already calculated for
    # this selected map point; no second weather request is made.
    current = payload["current"]
    payload["health"] = get_heat_health_recommendations_for_risk_payload({
        "location": {"city": f"Point({latitude:.4f}, {longitude:.4f})", "latitude": latitude, "longitude": longitude},
        "current": {"wbgt": current.get("wbgt_c"), "relativeRisk": current.get("relative_risk"), "attributableFraction": current.get("attributable_fraction"), "mortalityRiskIndex": current.get("mortality_risk_index"), "riskCategory": current.get("epidemiological_risk_category")},
        "forecast": [{"date": item["time"][:10], "wbgt": item.get("wbgt_c"), "relativeRisk": item.get("relative_risk"), "attributableFraction": item.get("attributable_fraction"), "mortalityRiskIndex": item.get("mortality_risk_index"), "riskCategory": item.get("epidemiological_risk_category")} for item in payload.get("daily_max_wbgt", [])],
    })
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _dashboard_cache[key] = {"created": time.time(), "payload": payload}
    return payload


def get_cached_heat_risk_for_city(city: str) -> Dict[str, Any]:
    key = city.strip().lower()
    cached = _heat_risk_cache.get(key)
    if cached and (time.time() - cached["created"] < CACHE_SECONDS):
        return cached["payload"]
    payload = fetch_heat_risk_for_city(city)
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _heat_risk_cache[key] = {"created": time.time(), "payload": payload}
    return payload


def get_cached_heat_risk_for_coords(latitude: float, longitude: float) -> Dict[str, Any]:
    key = f"{round(latitude, 4)},{round(longitude, 4)}"
    cached = _heat_risk_cache.get(key)
    if cached and (time.time() - cached["created"] < CACHE_SECONDS):
        return cached["payload"]
    payload = fetch_heat_risk_for_coordinates(latitude, longitude)
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _heat_risk_cache[key] = {"created": time.time(), "payload": payload}
    return payload


class HeatRiskApiHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIRECTORY, **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def _send_json(self, status: int, data: Dict[str, Any]) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, filename: str, content_type: str) -> None:
        filepath = os.path.join(STATIC_DIRECTORY, filename)
        if not os.path.exists(filepath):
            self.send_error(HTTPStatus.NOT_FOUND, f"File not found: {filename}")
            return
        with open(filepath, "rb") as f:
            content = f.read()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/recommendations":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
                data = json.loads(body)
                city = data.get("city")
                lat = data.get("lat") or data.get("latitude")
                lon = data.get("lon") or data.get("longitude")
                audience = data.get("audience", "PUBLIC")
                days = int(data.get("days", 5))
                if city:
                    self._send_json(HTTPStatus.OK, get_heat_health_recommendations(city, audience=audience, forecast_days=days))
                elif lat is not None and lon is not None:
                    lat_f, lon_f = float(lat), float(lon)
                    validate_location(lat_f, lon_f)
                    self._send_json(HTTPStatus.OK, get_heat_health_recommendations_for_coords(lat_f, lon_f, audience=audience, forecast_days=days))
                else:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Missing parameter. Provide 'city' or 'lat'+'lon'."})
            except ValueError as err:
                status = HTTPStatus.NOT_FOUND if "not found" in str(err).lower() else HTTPStatus.BAD_REQUEST
                self._send_json(status, {"error": str(err)})
            except Exception as err:
                self._send_json(HTTPStatus.BAD_GATEWAY, {"error": f"Failed to generate recommendations: {err}"})
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/health":
            self._send_json(HTTPStatus.OK, {"status": "healthy", "service": "heatwatch-india", "version": "3.0.0", "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
            return

        if path == "/api/wbgt-grid":
            try:
                self._send_json(HTTPStatus.OK, dashboard_grid())
            except Exception as err:
                self._send_json(HTTPStatus.BAD_GATEWAY, {"error": f"Could not build WBGT grid: {err}"})
            return

        if path == "/api/search":
            try:
                term = query.get("q", [""])[0].strip()
                if len(term) < 2:
                    raise ValueError("Enter at least two characters.")
                self._send_json(HTTPStatus.OK, {"results": geocode_city_list(term)})
            except ValueError as err:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(err)})
            except Exception as err:
                self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(err)})
            return

        if path == "/api/wbgt":
            try:
                city = query.get("city", [None])[0]
                lat_str = query.get("lat", [None])[0]
                lon_str = query.get("lon", [None])[0]
                if city:
                    geo = geocode_city(city)
                    lat, lon = geo["latitude"], geo["longitude"]
                elif lat_str is not None and lon_str is not None:
                    lat, lon = float(lat_str), float(lon_str)
                else:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Missing location. Provide ?lat=<lat>&lon=<lon> or ?city=<city>"}); return
                validate_location(lat, lon)
                self._send_json(HTTPStatus.OK, get_cached_dashboard(lat, lon))
            except ValueError as err:
                self._send_json(HTTPStatus.NOT_FOUND if "not found" in str(err).lower() else HTTPStatus.BAD_REQUEST, {"error": str(err)})
            except Exception as err:
                self._send_json(HTTPStatus.BAD_GATEWAY, {"error": f"Could not update WBGT: {err}"})
            return

        if path == "/api/heat-risk":
            try:
                city = query.get("city", [None])[0]
                lat_str = query.get("lat", [None])[0] or query.get("latitude", [None])[0]
                lon_str = query.get("lon", [None])[0] or query.get("longitude", [None])[0]
                if city:
                    self._send_json(HTTPStatus.OK, get_cached_heat_risk_for_city(city))
                elif lat_str is not None and lon_str is not None:
                    lat, lon = float(lat_str), float(lon_str)
                    validate_location(lat, lon)
                    self._send_json(HTTPStatus.OK, get_cached_heat_risk_for_coords(lat, lon))
                else:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Missing parameter. Provide ?city=<city> or ?lat=<lat>&lon=<lon>"})
            except ValueError as err:
                self._send_json(HTTPStatus.NOT_FOUND if "not found" in str(err).lower() else HTTPStatus.BAD_REQUEST, {"error": str(err)})
            except Exception as err:
                self._send_json(HTTPStatus.BAD_GATEWAY, {"error": f"Failed to compute heat risk: {err}"})
            return

        if path == "/api/recommendations":
            try:
                city = query.get("city", [None])[0]
                lat_str = query.get("lat", [None])[0] or query.get("latitude", [None])[0]
                lon_str = query.get("lon", [None])[0] or query.get("longitude", [None])[0]
                audience = query.get("audience", ["PUBLIC"])[0]
                days = int(query.get("days", ["5"])[0])
                if city:
                    self._send_json(HTTPStatus.OK, get_heat_health_recommendations(city, audience=audience, forecast_days=days))
                elif lat_str is not None and lon_str is not None:
                    lat, lon = float(lat_str), float(lon_str)
                    validate_location(lat, lon)
                    self._send_json(HTTPStatus.OK, get_heat_health_recommendations_for_coords(lat, lon, audience=audience, forecast_days=days))
                else:
                    self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Missing parameter. Provide ?city=<city> or ?lat=<lat>&lon=<lon>"})
            except ValueError as err:
                self._send_json(HTTPStatus.NOT_FOUND if "not found" in str(err).lower() else HTTPStatus.BAD_REQUEST, {"error": str(err)})
            except Exception as err:
                self._send_json(HTTPStatus.BAD_GATEWAY, {"error": f"Failed to generate recommendations: {err}"})
            return

        # Static files
        if path in ("/", "/index.html"):
            self._serve_file("index.html", "text/html; charset=utf-8"); return
        elif path == "/styles.css":
            self._serve_file("styles.css", "text/css; charset=utf-8"); return
        elif path == "/app.js":
            self._serve_file("app.js", "application/javascript; charset=utf-8"); return
        elif path == "/india-boundary.geojson":
            self._serve_file("india-boundary.geojson", "application/json; charset=utf-8"); return

        super().do_GET()


def create_server(host: str = "", port: int = 8000) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), HeatRiskApiHandler)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"HeatWatch India -- running at http://localhost:{port}")
    print(f"  Dashboard:       http://localhost:{port}/")
    print(f"  WBGT grid:       http://localhost:{port}/api/wbgt-grid")
    print(f"  City search:     http://localhost:{port}/api/search?q=Mumbai")
    print(f"  Heat risk:       http://localhost:{port}/api/heat-risk?city=Pune")
    print(f"  Recommendations: http://localhost:{port}/api/recommendations?city=Pune&audience=PUBLIC")
    print(f"  Health check:    http://localhost:{port}/api/health")
    server = create_server(port=port)
    server.serve_forever()

