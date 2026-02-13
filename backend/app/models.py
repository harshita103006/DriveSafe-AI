# app/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from .db import Base

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)

class Driver(Base):
    __tablename__ = "drivers"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    name = Column(String, index=True)

class Trip(Base):
    __tablename__ = "trips"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"), index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(String, nullable=True)

class Telemetry(Base):
    __tablename__ = "telemetry"
    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), index=True)
    ts = Column(DateTime(timezone=True), server_default=func.now())

    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    drowsy_score = Column(Float, default=0)      # 0-100 from frontend
    zone_risk = Column(Float, default=0)         # 0-100 from /risk/zone
    final_risk = Column(Float, default=0)        # combine