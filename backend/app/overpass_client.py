import httpx
from typing import Any, Dict

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def build_risk_query(lat: float, lng: float, radius_m: int) -> str:
    # Roads + signals/crossings + roundabouts
    # geom gives polyline points for "turniness"
    return f"""
    [out:json][timeout:25];
    (
      way(around:{radius_m},{lat},{lng})["highway"];
      node(around:{radius_m},{lat},{lng})["highway"="traffic_signals"];
      node(around:{radius_m},{lat},{lng})["highway"="crossing"];
      way(around:{radius_m},{lat},{lng})["junction"="roundabout"];
    );
    out body geom;
    """

def build_help_query(lat: float, lng: float, radius_m: int) -> str:
    return f"""
    [out:json][timeout:25];
    (
      node(around:{radius_m},{lat},{lng})["amenity"="hospital"];
      way(around:{radius_m},{lat},{lng})["amenity"="hospital"];
      relation(around:{radius_m},{lat},{lng})["amenity"="hospital"];

      node(around:{radius_m},{lat},{lng})["amenity"="police"];
      way(around:{radius_m},{lat},{lng})["amenity"="police"];
      relation(around:{radius_m},{lat},{lng})["amenity"="police"];

      node(around:{radius_m},{lat},{lng})["amenity"="shelter"];
      way(around:{radius_m},{lat},{lng})["amenity"="shelter"];
      relation(around:{radius_m},{lat},{lng})["amenity"="shelter"];

      node(around:{radius_m},{lat},{lng})["social_facility"="shelter"];
      way(around:{radius_m},{lat},{lng})["social_facility"="shelter"];
      relation(around:{radius_m},{lat},{lng})["social_facility"="shelter"];
    );
    out center 30;
    """

async def overpass_post(query: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        r = await client.post(
            OVERPASS_URL,
            data={"data": query},
            headers={
                "User-Agent": "DriveSafe-AI",
                "Accept": "application/json"
            }
        )

        r.raise_for_status()
        return r.json()