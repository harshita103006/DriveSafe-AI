from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ZoneRiskResponse(BaseModel):
    risk_score: int
    reasons: List[str]
    signals: Dict[str, Any]

class HelpItem(BaseModel):
    type: str
    name: str
    lat: float
    lng: float
    distance_m: float   # ✅ add this

class NearbyHelpResponse(BaseModel):
    hospitals: List[HelpItem]
    police: List[HelpItem]
    shelters: List[HelpItem]




class TripStartRequest(BaseModel):
    company_name: str
    driver_name: str
    notes: Optional[str] = None

class TripStartResponse(BaseModel):
    trip_id: int
    company_id: int
    driver_id: int

class TelemetryIn(BaseModel):
    trip_id: int
    lat: Optional[float] = None
    lng: Optional[float] = None
    drowsy_score: float
    zone_risk: float
    final_risk: float

class DashboardSummary(BaseModel):
    total_trips: int
    avg_final_risk: float
    max_final_risk: float
    safe_streak: int
    daily_avg_risk: List[Dict[str, Any]]  # [{"date":"2026-02-13","avg":42.1}]