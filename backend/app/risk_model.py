from typing import Any, Dict, List, Tuple
import math

ROAD_TYPE_RISK = {
    "motorway": 0.90,
    "trunk": 0.80,
    "primary": 0.70,
    "secondary": 0.60,
    "tertiary": 0.50,
    "residential": 0.30,
    "service": 0.25,
    "unclassified": 0.40,
}

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6371000.0
    to_rad = math.radians
    dlat = to_rad(lat2 - lat1)
    dlon = to_rad(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(to_rad(lat1))*math.cos(to_rad(lat2))*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def polyline_length_m(geom: List[Dict[str, float]]) -> float:
    if not geom or len(geom) < 2:
        return 0.0
    total = 0.0
    for i in range(1, len(geom)):
        total += haversine_m(geom[i-1]["lat"], geom[i-1]["lon"], geom[i]["lat"], geom[i]["lon"])
    return total

def bearing_deg(lat1, lon1, lat2, lon2) -> float:
    # bearing from point1 to point2
    y = math.sin(math.radians(lon2 - lon1)) * math.cos(math.radians(lat2))
    x = (math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) -
         math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(lon2 - lon1)))
    brng = math.degrees(math.atan2(y, x))
    return (brng + 360) % 360

def turniness_score(geom: List[Dict[str, float]]) -> float:
    # avg change in bearing; normalized to 0..1
    if not geom or len(geom) < 3:
        return 0.0
    changes = []
    for i in range(2, len(geom)):
        b1 = bearing_deg(geom[i-2]["lat"], geom[i-2]["lon"], geom[i-1]["lat"], geom[i-1]["lon"])
        b2 = bearing_deg(geom[i-1]["lat"], geom[i-1]["lon"], geom[i]["lat"], geom[i]["lon"])
        diff = abs(b2 - b1)
        diff = min(diff, 360 - diff)
        changes.append(diff)
    if not changes:
        return 0.0
    avg = sum(changes) / len(changes)  # 0..180
    return clamp(avg / 45.0, 0.0, 1.0)  # 45° avg change ~= max-ish

def parse_maxspeed(tag_val: Any) -> float:
    # returns speed in km/h (rough)
    if tag_val is None:
        return -1.0
    try:
        s = str(tag_val).lower().strip()
        # examples: "80", "50 mph"
        num = ""
        for ch in s:
            if ch.isdigit():
                num += ch
            elif num:
                break
        v = float(num) if num else -1.0
        if "mph" in s and v > 0:
            v = v * 1.60934
        return v
    except:
        return -1.0

def compute_zone_risk(osm_json: Dict[str, Any], radius_m: int) -> Tuple[int, Dict[str, Any], List[str]]:
    elements = osm_json.get("elements", [])

    signals = 0
    crossings = 0
    roundabouts = 0

    # Road aggregation
    road_len_by_type: Dict[str, float] = {}
    speeds: List[float] = []
    turn_scores: List[float] = []

    for el in elements:
        tags = el.get("tags", {}) or {}
        if el.get("type") == "node":
            if tags.get("highway") == "traffic_signals":
                signals += 1
            if tags.get("highway") == "crossing":
                crossings += 1

        if el.get("type") == "way":
            hwy = tags.get("highway")
            if hwy:
                geom = el.get("geometry") or []
                length_m = polyline_length_m(geom)
                road_len_by_type[hwy] = road_len_by_type.get(hwy, 0.0) + length_m

                ms = parse_maxspeed(tags.get("maxspeed"))
                if ms > 0:
                    speeds.append(ms)

                turn_scores.append(turniness_score(geom))

            if tags.get("junction") == "roundabout":
                roundabouts += 1

    # Road-type risk: weighted by length
    total_len = sum(road_len_by_type.values()) or 1.0
    road_type_risk = 0.0
    top_road_type = None
    top_len = 0.0
    for t, ln in road_len_by_type.items():
        w = ln / total_len
        road_type_risk += w * ROAD_TYPE_RISK.get(t, 0.45)
        if ln > top_len:
            top_len = ln
            top_road_type = t

    # Speed risk
    if speeds:
        avg_speed = sum(speeds) / len(speeds)
        speed_risk = clamp((avg_speed - 40) / 60, 0.0, 1.0)  # 40->0, 100->1
    else:
        avg_speed = None
        # fallback: infer from road_type_risk
        speed_risk = clamp((road_type_risk - 0.3) / 0.6, 0.0, 1.0)

    # Intersection density risk (signals + crossings + roundabouts)
    area_km2 = math.pi * (radius_m / 1000.0) ** 2
    density = (signals + crossings + 2 * roundabouts) / max(area_km2, 0.1)
    # normalize: 0..~15 per km2
    intersection_risk = clamp(density / 12.0, 0.0, 1.0)

    # Turn risk
    turn_risk = clamp((sum(turn_scores) / len(turn_scores)) if turn_scores else 0.0, 0.0, 1.0)

    # Final risk
    risk = 100.0 * (
        0.35 * road_type_risk +
        0.25 * speed_risk +
        0.25 * intersection_risk +
        0.15 * turn_risk
    )
    risk_score = int(round(clamp(risk, 0.0, 100.0)))

    # Reasons
    reasons = []
    # pick top two
    candidates = [
        ("High-speed roads nearby", speed_risk),
        ("Many intersections/crossings", intersection_risk),
        ("Sharp turns/curvy roads", turn_risk),
        (f"Road type risk ({top_road_type})", road_type_risk),
    ]
    candidates.sort(key=lambda x: x[1], reverse=True)
    for text, val in candidates[:2]:
        if val >= 0.35:
            reasons.append(text)
    if not reasons:
        reasons = ["Normal road context"]

    signals_out = {
        "radius_m": radius_m,
        "signals": signals,
        "crossings": crossings,
        "roundabouts": roundabouts,
        "dominant_road_type": top_road_type,
        "road_type_risk": round(road_type_risk, 3),
        "avg_maxspeed_kmh": (round(avg_speed, 1) if avg_speed is not None else None),
        "speed_risk": round(speed_risk, 3),
        "intersection_density_per_km2": round(density, 2),
        "intersection_risk": round(intersection_risk, 3),
        "turn_risk": round(turn_risk, 3),
        "road_length_by_type_m": {k: int(v) for k, v in road_len_by_type.items()},
    }
    return risk_score, signals_out, reasons