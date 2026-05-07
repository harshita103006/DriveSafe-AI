const API_BASE = "http://localhost:8000";

export async function startTrip(driverId="demo_driver") {
  const res = await fetch(`${API_BASE}/api/trips/start`, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ driver_id: driverId })
  });
  return res.json();
}

export async function endTrip(tripId) {
  await fetch(`${API_BASE}/api/trips/${tripId}/end`, { method: "POST" });
}

export async function postEvent(tripId, event, meta={}) {
  await fetch(`${API_BASE}/api/events`, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ trip_id: tripId, event, meta })
  });
}