"""Small no-dependency server for the live WBGT GIS dashboard.

Run ``python3 dashboard_server.py`` then open http://localhost:8000.
"""
import json
import os
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen

from weather_api import (CURRENT_FIELDS, build_dashboard_payload,
                         calculate_current_wbgt, fetch_weather_snapshot,
                         validate_location)


STATIC_DIRECTORY = os.path.join(os.path.dirname(__file__), "dashboard")
CACHE_SECONDS = 300
_cache = {}

# CC0 geoBoundaries ADM0 geometry (WGS84).  This dataset is also fetched by
# the client to clip the rendered field.  Keeping the grid mask here prevents
# weather calls outside the actual country geometry.
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
    """Test a WGS84 point against the high-resolution country geometry."""
    for polygon in INDIA_POLYGONS:
        if point_in_ring(lon, lat, polygon[0]) and not any(point_in_ring(lon, lat, hole) for hole in polygon[1:]):
            return True
    return False


def spatial_grid_points(step=2.0):
    return [(round(lat, 3), round(lon, 3)) for lat in frange(8, 35, step)
            for lon in frange(68, 97, step) if point_in_india(lon, lat)]


def frange(start, stop, step):
    while start <= stop:
        yield start
        start += step


def dashboard_grid():
    """Return current, genuine WBGT observations for an India-wide grid.

    Open-Meteo accepts coordinate lists in one request.  This avoids browser
    fan-out and gives the map one authoritative backend-generated data source.
    """
    key = "india-grid"
    cached = _cache.get(key)
    if cached and time.time() - cached["created"] < CACHE_SECONDS:
        return cached["payload"]
    points = spatial_grid_points()
    params = {"latitude": ",".join(str(p[0]) for p in points),
              "longitude": ",".join(str(p[1]) for p in points),
              "current": ",".join(CURRENT_FIELDS), "timezone": "GMT",
              "wind_speed_unit": "ms"}
    with urlopen("https://api.open-meteo.com/v1/forecast?" + urlencode(params), timeout=25) as response:
        snapshots = json.loads(response.read().decode("utf-8"))
    if not isinstance(snapshots, list):
        snapshots = [snapshots]
    observations = []
    for requested, snapshot in zip(points, snapshots):
        lat, lon = snapshot.get("latitude", requested[0]), snapshot.get("longitude", requested[1])
        current = calculate_current_wbgt(snapshot, lat, lon)
        if current["wbgt_c"] is not None:
            observations.append({"lat": lat, "lon": lon, "wbgt_c": current["wbgt_c"], "risk": current["risk"]})
    payload = {"points": observations, "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    _cache[key] = {"created": time.time(), "payload": payload}
    return payload


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
    {"name": "Pimpri-Chinchwad", "admin1": "Maharashtra", "lat": 18.6298, "lon": 73.7997, "country": "India"},
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
    {"name": "Allahabad", "admin1": "Uttar Pradesh", "lat": 25.4358, "lon": 81.8463, "country": "India"},
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
    {"name": "Bhavnagar", "admin1": "Gujarat", "lat": 21.7645, "lon": 72.1519, "country": "India"},
    {"name": "Ujjain", "admin1": "Madhya Pradesh", "lat": 23.1765, "lon": 75.7885, "country": "India"},
    {"name": "Nellore", "admin1": "Andhra Pradesh", "lat": 14.4426, "lon": 79.9865, "country": "India"},
    {"name": "Kurnool", "admin1": "Andhra Pradesh", "lat": 15.8281, "lon": 78.0373, "country": "India"},
    {"name": "Manali", "admin1": "Himachal Pradesh", "lat": 32.2432, "lon": 77.1892, "country": "India"},
    {"name": "Kullu", "admin1": "Himachal Pradesh", "lat": 31.9579, "lon": 77.1095, "country": "India"},
    {"name": "Dharamshala", "admin1": "Himachal Pradesh", "lat": 32.2190, "lon": 76.3234, "country": "India"},
    {"name": "Rishikesh", "admin1": "Uttarakhand", "lat": 30.0869, "lon": 78.2676, "country": "India"},
    {"name": "Haridwar", "admin1": "Uttarakhand", "lat": 29.9457, "lon": 78.1642, "country": "India"},
    {"name": "Nainital", "admin1": "Uttarakhand", "lat": 29.3919, "lon": 79.4542, "country": "India"},
    {"name": "Mussoorie", "admin1": "Uttarakhand", "lat": 30.4598, "lon": 78.0644, "country": "India"},
    {"name": "Ooty", "admin1": "Tamil Nadu", "lat": 11.4102, "lon": 76.6950, "country": "India"},
    {"name": "Kodaikanal", "admin1": "Tamil Nadu", "lat": 10.2381, "lon": 77.4892, "country": "India"},
    {"name": "Munnar", "admin1": "Kerala", "lat": 10.0889, "lon": 77.0595, "country": "India"},
    {"name": "Wayanad", "admin1": "Kerala", "lat": 11.6854, "lon": 76.1320, "country": "India"},
    {"name": "Alappuzha", "admin1": "Kerala", "lat": 9.4981, "lon": 76.3388, "country": "India"},
    {"name": "Darjeeling", "admin1": "West Bengal", "lat": 27.0410, "lon": 88.2663, "country": "India"},
    {"name": "Kalimpong", "admin1": "West Bengal", "lat": 27.0667, "lon": 88.4667, "country": "India"},
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
    {"name": "Bhagalpur", "admin1": "Bihar", "lat": 25.2425, "lon": 86.9842, "country": "India"},
    {"name": "Bhilai", "admin1": "Chhattisgarh", "lat": 21.1938, "lon": 81.3509, "country": "India"},
    {"name": "Bilaspur", "admin1": "Chhattisgarh", "lat": 22.0797, "lon": 82.1409, "country": "India"},
    {"name": "Gandhinagar", "admin1": "Gujarat", "lat": 23.2156, "lon": 72.6369, "country": "India"},
    {"name": "Junagadh", "admin1": "Gujarat", "lat": 21.5222, "lon": 70.4579, "country": "India"},
    {"name": "Anand", "admin1": "Gujarat", "lat": 22.5645, "lon": 72.9289, "country": "India"},
    {"name": "Karnal", "admin1": "Haryana", "lat": 29.6857, "lon": 76.9905, "country": "India"},
    {"name": "Panipat", "admin1": "Haryana", "lat": 29.3909, "lon": 76.9635, "country": "India"},
    {"name": "Rohtak", "admin1": "Haryana", "lat": 28.8955, "lon": 76.6066, "country": "India"},
    {"name": "Hisar", "admin1": "Haryana", "lat": 29.1492, "lon": 75.7217, "country": "India"},
    {"name": "Ambala", "admin1": "Haryana", "lat": 30.3782, "lon": 76.7767, "country": "India"},
    {"name": "Bokaro", "admin1": "Jharkhand", "lat": 23.6693, "lon": 86.1511, "country": "India"},
    {"name": "Deoghar", "admin1": "Jharkhand", "lat": 24.4826, "lon": 86.7001, "country": "India"},
    {"name": "Udupi", "admin1": "Karnataka", "lat": 13.3409, "lon": 74.7421, "country": "India"},
    {"name": "Kalaburagi", "admin1": "Karnataka", "lat": 17.3297, "lon": 76.8343, "country": "India"},
    {"name": "Davanagere", "admin1": "Karnataka", "lat": 14.4644, "lon": 75.9218, "country": "India"},
    {"name": "Ballari", "admin1": "Karnataka", "lat": 15.1394, "lon": 76.9214, "country": "India"},
    {"name": "Kollam", "admin1": "Kerala", "lat": 8.8932, "lon": 76.6141, "country": "India"},
    {"name": "Thrissur", "admin1": "Kerala", "lat": 10.5276, "lon": 76.2144, "country": "India"},
    {"name": "Kannur", "admin1": "Kerala", "lat": 11.8745, "lon": 75.3704, "country": "India"},
    {"name": "Sagar", "admin1": "Madhya Pradesh", "lat": 23.8388, "lon": 78.7378, "country": "India"},
    {"name": "Satna", "admin1": "Madhya Pradesh", "lat": 24.5824, "lon": 80.8299, "country": "India"},
    {"name": "Ratlam", "admin1": "Madhya Pradesh", "lat": 23.3315, "lon": 75.0367, "country": "India"},
    {"name": "Sangli", "admin1": "Maharashtra", "lat": 16.8524, "lon": 74.5815, "country": "India"},
    {"name": "Satara", "admin1": "Maharashtra", "lat": 17.6805, "lon": 73.9935, "country": "India"},
    {"name": "Amravati", "admin1": "Maharashtra", "lat": 20.9374, "lon": 77.7796, "country": "India"},
    {"name": "Akola", "admin1": "Maharashtra", "lat": 20.7002, "lon": 77.0082, "country": "India"},
    {"name": "Latur", "admin1": "Maharashtra", "lat": 18.4088, "lon": 76.5604, "country": "India"},
    {"name": "Dhule", "admin1": "Maharashtra", "lat": 20.9042, "lon": 74.7749, "country": "India"},
    {"name": "Jalgaon", "admin1": "Maharashtra", "lat": 21.0077, "lon": 75.5626, "country": "India"},
    {"name": "Chandrapur", "admin1": "Maharashtra", "lat": 19.9615, "lon": 79.2961, "country": "India"},
    {"name": "Nanded", "admin1": "Maharashtra", "lat": 19.1383, "lon": 77.3210, "country": "India"},
    {"name": "Ahmednagar", "admin1": "Maharashtra", "lat": 19.0948, "lon": 74.7480, "country": "India"},
    {"name": "Shirdi", "admin1": "Maharashtra", "lat": 19.7667, "lon": 74.4764, "country": "India"},
    {"name": "Mahabaleshwar", "admin1": "Maharashtra", "lat": 17.9307, "lon": 73.6477, "country": "India"},
    {"name": "Ratnagiri", "admin1": "Maharashtra", "lat": 16.9902, "lon": 73.3120, "country": "India"},
    {"name": "Puri", "admin1": "Odisha", "lat": 19.8135, "lon": 85.8312, "country": "India"},
    {"name": "Cuttack", "admin1": "Odisha", "lat": 20.4625, "lon": 85.8828, "country": "India"},
    {"name": "Rourkela", "admin1": "Odisha", "lat": 22.2604, "lon": 84.8536, "country": "India"},
    {"name": "Sambalpur", "admin1": "Odisha", "lat": 21.4669, "lon": 83.9812, "country": "India"},
    {"name": "Jalandhar", "admin1": "Punjab", "lat": 31.3260, "lon": 75.5762, "country": "India"},
    {"name": "Patiala", "admin1": "Punjab", "lat": 30.3398, "lon": 76.3869, "country": "India"},
    {"name": "Bathinda", "admin1": "Punjab", "lat": 30.2110, "lon": 74.9455, "country": "India"},
    {"name": "Mohali", "admin1": "Punjab", "lat": 30.7046, "lon": 76.7179, "country": "India"},
    {"name": "Ajmer", "admin1": "Rajasthan", "lat": 26.4499, "lon": 74.6399, "country": "India"},
    {"name": "Bikaner", "admin1": "Rajasthan", "lat": 28.0229, "lon": 73.3119, "country": "India"},
    {"name": "Alwar", "admin1": "Rajasthan", "lat": 27.5530, "lon": 76.6346, "country": "India"},
    {"name": "Bhilwara", "admin1": "Rajasthan", "lat": 25.3407, "lon": 74.6313, "country": "India"},
    {"name": "Jaisalmer", "admin1": "Rajasthan", "lat": 26.9157, "lon": 70.9083, "country": "India"},
    {"name": "Mount Abu", "admin1": "Rajasthan", "lat": 24.5926, "lon": 72.7156, "country": "India"},
    {"name": "Tiruppur", "admin1": "Tamil Nadu", "lat": 11.1085, "lon": 77.3411, "country": "India"},
    {"name": "Erode", "admin1": "Tamil Nadu", "lat": 11.3410, "lon": 77.7172, "country": "India"},
    {"name": "Vellore", "admin1": "Tamil Nadu", "lat": 12.9165, "lon": 79.1325, "country": "India"},
    {"name": "Tirunelveli", "admin1": "Tamil Nadu", "lat": 8.7139, "lon": 77.7567, "country": "India"},
    {"name": "Thoothukudi", "admin1": "Tamil Nadu", "lat": 8.7642, "lon": 78.1348, "country": "India"},
    {"name": "Thanjavur", "admin1": "Tamil Nadu", "lat": 10.7870, "lon": 79.1378, "country": "India"},
    {"name": "Kanyakumari", "admin1": "Tamil Nadu", "lat": 8.0883, "lon": 77.5385, "country": "India"},
    {"name": "Rameswaram", "admin1": "Tamil Nadu", "lat": 9.2876, "lon": 79.3129, "country": "India"},
    {"name": "Warangal", "admin1": "Telangana", "lat": 17.9689, "lon": 79.5941, "country": "India"},
    {"name": "Nizamabad", "admin1": "Telangana", "lat": 18.6725, "lon": 78.0941, "country": "India"},
    {"name": "Karimnagar", "admin1": "Telangana", "lat": 18.4386, "lon": 79.1288, "country": "India"},
    {"name": "Khammam", "admin1": "Telangana", "lat": 17.2473, "lon": 80.1514, "country": "India"},
    {"name": "Gorakhpur", "admin1": "Uttar Pradesh", "lat": 26.7606, "lon": 83.3732, "country": "India"},
    {"name": "Jhansi", "admin1": "Uttar Pradesh", "lat": 25.4484, "lon": 78.5685, "country": "India"},
    {"name": "Saharanpur", "admin1": "Uttar Pradesh", "lat": 29.9640, "lon": 77.5460, "country": "India"},
    {"name": "Moradabad", "admin1": "Uttar Pradesh", "lat": 28.8386, "lon": 78.7733, "country": "India"},
    {"name": "Mathura", "admin1": "Uttar Pradesh", "lat": 27.4924, "lon": 77.6737, "country": "India"},
    {"name": "Ayodhya", "admin1": "Uttar Pradesh", "lat": 26.7922, "lon": 82.1998, "country": "India"},
    {"name": "Muzaffarnagar", "admin1": "Uttar Pradesh", "lat": 29.4727, "lon": 77.7085, "country": "India"},
    {"name": "Siliguri", "admin1": "West Bengal", "lat": 26.7271, "lon": 88.3953, "country": "India"},
    {"name": "Asansol", "admin1": "West Bengal", "lat": 23.6739, "lon": 86.9524, "country": "India"},
    {"name": "Durgapur", "admin1": "West Bengal", "lat": 23.5204, "lon": 87.3119, "country": "India"},
]


def geocode_city(query):
    query_clean = query.strip()
    q_lower = query_clean.lower()
    search_terms = [query_clean]
    if q_lower in CITY_ALIASES and CITY_ALIASES[q_lower].lower() != q_lower:
        search_terms.append(CITY_ALIASES[q_lower])

    seen = set()
    results = []

    # 1. Local major cities lookup
    for city in PREDEFINED_INDIAN_CITIES:
        c_name = city["name"].lower()
        if q_lower == c_name or q_lower in c_name or c_name.startswith(q_lower) or any(t.lower() in c_name for t in search_terms):
            key = (round(city["lat"], 2), round(city["lon"], 2))
            if key not in seen:
                seen.add(key)
                results.append(dict(city))

    # 2. Remote geocoding with Open-Meteo
    for term in search_terms:
        try:
            url = "https://geocoding-api.open-meteo.com/v1/search?" + urlencode({"name": term, "count": 40, "language": "en", "format": "json"})
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
                        results.append({"name": item["name"], "admin1": item.get("admin1", ""), "country": item.get("country", "India"),
                                        "lat": lat, "lon": lon})
        except Exception:
            pass

    return results


def dashboard_for_location(latitude, longitude):
    """Fetch/calculate one location, caching briefly for map refreshes."""
    key = (round(latitude, 4), round(longitude, 4))
    cached = _cache.get(key)
    if cached and time.time() - cached["created"] < CACHE_SECONDS:
        return cached["payload"]
    payload = build_dashboard_payload(fetch_weather_snapshot(latitude=latitude, longitude=longitude), latitude, longitude)
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _cache[key] = {"created": time.time(), "payload": payload}
    return payload


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/wbgt", "/api/wbgt-grid", "/api/search"}:
            return super().do_GET()
        try:
            query = parse_qs(parsed.query)
            if parsed.path == "/api/wbgt-grid":
                result = dashboard_grid()
            elif parsed.path == "/api/search":
                term = query.get("q", [""])[0].strip()
                if len(term) < 2: raise ValueError("Enter at least two characters.")
                result = {"results": geocode_city(term)}
            else:
                latitude, longitude = float(query["lat"][0]), float(query["lon"][0])
                validate_location(latitude, longitude)
                result = dashboard_for_location(latitude, longitude)
            body, status = json.dumps(result).encode(), HTTPStatus.OK
        except (KeyError, ValueError) as error:
            body, status = json.dumps({"error": f"Invalid location: {error}"}).encode(), HTTPStatus.BAD_REQUEST
        except Exception as error:  # Keep Open-Meteo/upstream errors visible in the dashboard.
            body, status = json.dumps({"error": f"Could not update WBGT: {error}"}).encode(), HTTPStatus.BAD_GATEWAY
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print("WBGT GIS dashboard: http://localhost:8000")
    ThreadingHTTPServer(("", 8000), DashboardHandler).serve_forever()
