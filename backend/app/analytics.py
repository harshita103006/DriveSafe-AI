# app/analytics.py
from sqlalchemy import select, func, desc,case
from .db import SessionLocal
from .models import Trip, Telemetry

async def dashboard_summary(company_id: int, driver_id: int | None = None):
    async with SessionLocal() as db:
        trip_q = select(func.count(Trip.id)).where(Trip.company_id == company_id)
        if driver_id:
            trip_q = trip_q.where(Trip.driver_id == driver_id)
        total_trips = (await db.execute(trip_q)).scalar() or 0

        tel_q = select(
            func.avg(Telemetry.final_risk),
            func.max(Telemetry.final_risk)
        ).select_from(Telemetry).join(Trip, Trip.id == Telemetry.trip_id).where(Trip.company_id == company_id)
        if driver_id:
            tel_q = tel_q.where(Trip.driver_id == driver_id)

        avg_risk, max_risk = (await db.execute(tel_q)).one()
        avg_risk = float(avg_risk or 0)
        max_risk = float(max_risk or 0)

        # daily avg for chart
        daily_q = select(
            func.date(Telemetry.ts).label("d"),
            func.avg(Telemetry.final_risk).label("avg")
        ).select_from(Telemetry).join(Trip, Trip.id == Telemetry.trip_id).where(Trip.company_id == company_id).group_by("d").order_by(desc("d")).limit(14)

        daily_rows = (await db.execute(daily_q)).all()
        daily = [{"date": str(r.d), "avg": float(r.avg or 0)} for r in reversed(daily_rows)]

        # safe streak: last N trips where avg risk < 30
        # (simple version: compute from last 20 trips)
        last_trips_q = select(Trip.id).where(Trip.company_id == company_id).order_by(desc(Trip.started_at)).limit(20)
        if driver_id:
            last_trips_q = last_trips_q.where(Trip.driver_id == driver_id)
        last_trip_ids = [x[0] for x in (await db.execute(last_trips_q)).all()]

        streak = 0
        for tid in last_trip_ids:
            avg_trip = (await db.execute(select(func.avg(Telemetry.final_risk)).where(Telemetry.trip_id == tid))).scalar() or 0
            if float(avg_trip) < 30:
                streak += 1
            else:
                break

        return total_trips, avg_risk, max_risk, streak, daily
    
from datetime import datetime, timedelta

async def timeseries_risk(trip_id: int, limit: int = 200):
    """
    Returns chart-ready points: [{ts, drowsy, zone, final}]
    """
    async with SessionLocal() as db:
        q = select(
            Telemetry.ts,
            Telemetry.drowsy_score,
            Telemetry.zone_risk,
            Telemetry.final_risk
        ).where(Telemetry.trip_id == trip_id).order_by(Telemetry.id.desc()).limit(limit)

        rows = (await db.execute(q)).all()

    rows = list(reversed(rows))
    return [
        {
            "ts": r.ts.isoformat() if r.ts else None,
            "drowsy": float(r.drowsy_score or 0),
            "zone": float(r.zone_risk or 0),
            "final": float(r.final_risk or 0),
        }
        for r in rows
    ]


async def daily_metrics(company_id: int, days: int = 14, driver_id: int | None = None):
    """
    Returns multi-series daily chart:
    [{date, avg_final, max_final, events_high}]
    """
    async with SessionLocal() as db:
        base = select(
            func.date(Telemetry.ts).label("d"),
            func.avg(Telemetry.final_risk).label("avg_final"),
            func.max(Telemetry.final_risk).label("max_final"),
            func.sum(case((Telemetry.final_risk >= 70, 1), else_=0)).label("events_high"),
        ).select_from(Telemetry).join(Trip, Trip.id == Telemetry.trip_id)\
         .where(Trip.company_id == company_id)

        if driver_id:
            base = base.where(Trip.driver_id == driver_id)

        base = base.group_by("d").order_by(desc("d")).limit(days)

        rows = (await db.execute(base)).all()

    rows = list(reversed(rows))
    return [
        {
            "date": str(r.d),
            "avg_final": round(float(r.avg_final or 0), 1),
            "max_final": round(float(r.max_final or 0), 1),
            "events_high": int(r.events_high or 0),
        }
        for r in rows
    ]