import math
from typing import List, Dict

def offset_lat_lng(lat: float, lng: float, meters_north: float, meters_east: float):
    # approx conversion
    dlat = meters_north / 111_320.0
    dlng = meters_east / (111_320.0 * math.cos(math.radians(lat)))
    return lat + dlat, lng + dlng

def make_grid(lat: float, lng: float, grid: int = 5, spacing_m: int = 250) -> List[Dict]:
    """
    grid=5 -> 5x5 points, spacing 250m
    returns points with lat/lng and grid coords
    """
    half = grid // 2
    pts = []
    for i in range(-half, half + 1):
        for j in range(-half, half + 1):
            lat2, lng2 = offset_lat_lng(lat, lng, i * spacing_m, j * spacing_m)
            pts.append({"i": i, "j": j, "lat": lat2, "lng": lng2})
    return pts