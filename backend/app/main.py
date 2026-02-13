from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Dict, List
from .overpass_client import build_risk_query, build_help_query, overpass_post
from .risk_model import compute_zone_risk
from .schemas import ZoneRiskResponse, NearbyHelpResponse, HelpItem
from math import radians, sin, cos, asin, sqrt
from .db import engine, Base
from .crud import get_or_create_company, get_or_create_driver, create_trip, add_telemetry
from .analytics import dashboard_summary
from .schemas import TripStartRequest, TripStartResponse, TelemetryIn, DashboardSummary
from .predict import predict_next_risk
from datetime import datetime
from sqlalchemy import select
from .models import Telemetry
from sqlalchemy import select
from .models import Company, Driver, Trip
from .db import SessionLocal
from .analytics import timeseries_risk, daily_metrics
import asyncio
from .heatmap import make_grid
import time
import httpx

app = FastAPI(title="DriveSafe-AI Backend", version="1.0")

# CORS so frontend can call later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hackathon mode; later set specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
_HEATMAP_CACHE = {}  # key -> (timestamp, data)
def _haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/risk/zone", response_model=ZoneRiskResponse)
async def zone_risk(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius: int = Query(1000, ge=200, le=5000),
):
    query = build_risk_query(lat, lng, radius)
    osm = await overpass_post(query)
    risk_score, signals, reasons = compute_zone_risk(osm, radius)
    return ZoneRiskResponse(risk_score=risk_score, reasons=reasons, signals=signals)

def _extract_help_items(osm: Dict[str, Any], wanted: str, lat: float, lng: float) -> List[HelpItem]:
    out: List[HelpItem] = []
    for el in osm.get("elements", []):
        tags = el.get("tags", {}) or {}
        t = tags.get("amenity") or tags.get("social_facility")
        if wanted == "shelter":
            if not (tags.get("amenity") == "shelter" or tags.get("social_facility") == "shelter"):
                continue
        else:
            if tags.get("amenity") != wanted:
                continue

        name = tags.get("name") or "Unnamed"
        lat2 = el.get("lat") or (el.get("center") or {}).get("lat")
        lng2 = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat2 is None or lng2 is None:
            continue

        typ = "Hospital" if wanted == "hospital" else "Police" if wanted == "police" else "Shelter"
        dist = _haversine_m(lat, lng, float(lat2), float(lng2))
        out.append(HelpItem(type=typ, name=name, lat=float(lat2), lng=float(lng2), distance_m=round(dist, 1)))
    out.sort(key=lambda x: x.distance_m)
    return out[:15]

@app.get("/nearby/help", response_model=NearbyHelpResponse)
async def nearby_help(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius: int = Query(3000, ge=500, le=10000),
):
    query = build_help_query(lat, lng, radius)
    osm = await overpass_post(query)
    hospitals = _extract_help_items(osm, "hospital", lat, lng)
    police = _extract_help_items(osm, "police", lat, lng)
    shelters = _extract_help_items(osm, "shelter", lat, lng)
    return NearbyHelpResponse(hospitals=hospitals, police=police, shelters=shelters)

@app.get("/emergency")
async def emergency(country: str = "IN"):
    if country.upper() == "IN":
        return {
            "primary": "112",
            "others": [
                {"name": "Ambulance", "number": "108"},
                {"name": "Police", "number": "100"},
                {"name": "Fire", "number": "101"}
            ]
        }
    return {"primary": "112", "others": []}

@app.get("/risk/combined")
async def combined_risk(
    lat: float,
    lng: float,
    drowsy_score: float,   # frontend se aayega (0-100)
    radius: int = 1000,
):
    query = build_risk_query(lat, lng, radius)
    osm = await overpass_post(query)
    zone_risk, signals, reasons = compute_zone_risk(osm, radius)

    final_risk = int(0.6 * zone_risk + 0.4 * drowsy_score)

    alert_level = "SAFE"
    if final_risk > 75:
        alert_level = "CRITICAL"
    elif final_risk > 50:
        alert_level = "HIGH"
    elif final_risk > 30:
        alert_level = "MEDIUM"

    return {
        "zone_risk": zone_risk,
        "drowsy_score": drowsy_score,
        "final_risk": final_risk,
        "alert_level": alert_level,
        "reasons": reasons
    }

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.post("/trips/start", response_model=TripStartResponse)
async def trips_start(payload: TripStartRequest):
    company = await get_or_create_company(payload.company_name)
    driver = await get_or_create_driver(company.id, payload.driver_name)
    trip = await create_trip(company.id, driver.id, payload.notes)
    return TripStartResponse(trip_id=trip.id, company_id=company.id, driver_id=driver.id)

@app.post("/telemetry")
async def telemetry(payload: TelemetryIn):
    await add_telemetry(payload.model_dump())
    return {"ok": True}

@app.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard(company_id: int, driver_id: int | None = None):
    total, avg_risk, max_risk, streak, daily = await dashboard_summary(company_id, driver_id)
    return DashboardSummary(
        total_trips=total,
        avg_final_risk=round(avg_risk, 1),
        max_final_risk=round(max_risk, 1),
        safe_streak=streak,
        daily_avg_risk=daily
    )

@app.get("/predict/next")
async def predict_next(trip_id: int, minutes_since_start: int):
    # pull last 30 telemetry points
    async with SessionLocal() as db:
        rows = (await db.execute(
            select(Telemetry.final_risk).where(Telemetry.trip_id == trip_id).order_by(Telemetry.id.desc()).limit(30)
        )).all()
    recent = [float(r[0]) for r in reversed(rows)]
    hour = datetime.now().hour
    return predict_next_risk(recent, minutes_since_start, hour)

@app.get("/fleet/drivers")
async def fleet_drivers(company_id: int):
    async with SessionLocal() as db:
        rows = (await db.execute(select(Driver).where(Driver.company_id == company_id))).scalars().all()
    return [{"driver_id": d.id, "name": d.name} for d in rows]

@app.get("/fleet/trips/recent")
async def fleet_recent_trips(company_id: int, limit: int = 20):
    async with SessionLocal() as db:
        trips = (await db.execute(
            select(Trip).where(Trip.company_id == company_id).order_by(Trip.started_at.desc()).limit(limit)
        )).scalars().all()
    return [{"trip_id": t.id, "driver_id": t.driver_id, "started_at": str(t.started_at), "ended_at": str(t.ended_at) if t.ended_at else None} for t in trips]

@app.get("/charts/trip")
async def chart_trip(trip_id: int, limit: int = 200):
    points = await timeseries_risk(trip_id, limit)
    return {"trip_id": trip_id, "points": points}

@app.get("/charts/daily")
async def chart_daily(company_id: int, days: int = 14, driver_id: int | None = None):
    points = await daily_metrics(company_id, days, driver_id)
    return {"company_id": company_id, "points": points}

@app.get("/risk/heatmap")
async def risk_heatmap(
    lat: float,
    lng: float,
    radius: int = 600,
    grid: int = 5,
    spacing_m: int = 250,
    cache_sec: int = 120
):
    key = (round(lat, 4), round(lng, 4), radius, grid, spacing_m)
    now = time.time()

    # ✅ cache
    if key in _HEATMAP_CACHE:
        ts, cached = _HEATMAP_CACHE[key]
        if now - ts < cache_sec:
            return cached

    pts = make_grid(lat, lng, grid=grid, spacing_m=spacing_m)

    async def score_point(p):
        # ✅ retry 2 times
        for attempt in range(3):
            try:
                query = build_risk_query(p["lat"], p["lng"], radius)
                osm = await overpass_post(query)
                risk_score, _, _ = compute_zone_risk(osm, radius)
                return {
                    "i": p["i"], "j": p["j"],
                    "lat": p["lat"], "lng": p["lng"],
                    "risk_score": int(risk_score)
                }
            except (httpx.HTTPError, Exception):
                if attempt == 2:
                    # ✅ fallback: center risk as default
                    return {
                        "i": p["i"], "j": p["j"],
                        "lat": p["lat"], "lng": p["lng"],
                        "risk_score": None
                    }

    results = await asyncio.gather(*[score_point(p) for p in pts])

    data = {"center": {"lat": lat, "lng": lng}, "grid": grid, "spacing_m": spacing_m, "points": results}
    _HEATMAP_CACHE[key] = (now, data)
    return data