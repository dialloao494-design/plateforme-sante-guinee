"""Geodesic helpers for doctor discovery (Haversine)."""


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import asin, atan2, cos, radians, sin, sqrt

    r = 6371.0
    p1, p2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlmb = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(p1) * cos(p2) * sin(dlmb / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return r * c
