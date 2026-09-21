import math
import random
from typing import Tuple

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the great-circle distance between two points on Earth in kilometers.
    """
    R = 6371.0  # Earth radius in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) *
         math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return round(R * c, 3)

def fuzz_donor_location(lat: float, lon: float, fuzz_radius_meters: float = 800.0) -> Tuple[float, float]:
    """
    Fuzzes a donor's geographic location by introducing random jitter within fuzz_radius_meters.
    Used to protect donor residential privacy before an explicit match is accepted.
    """
    # 1 deg latitude is approx 111,320 meters
    # 1 deg longitude is approx 111,320 * cos(lat) meters
    radius_in_degrees = fuzz_radius_meters / 111320.0
    u = random.random()
    v = random.random()
    w = radius_in_degrees * math.sqrt(u)
    t = 2.0 * math.pi * v
    x = w * math.cos(t)
    y = w * math.sin(t)

    fuzzed_lat = lat + y
    fuzzed_lon = lon + (x / math.cos(math.radians(lat)))
    return round(fuzzed_lat, 4), round(fuzzed_lon, 4)
