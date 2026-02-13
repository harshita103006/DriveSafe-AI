# app/crud.py
from sqlalchemy import select
from .db import SessionLocal
from .models import Company, Driver, Trip, Telemetry

async def get_or_create_company(name: str) -> Company:
    async with SessionLocal() as db:
        res = await db.execute(select(Company).where(Company.name == name))
        company = res.scalar_one_or_none()
        if company:
            return company
        company = Company(name=name)
        db.add(company)
        await db.commit()
        await db.refresh(company)
        return company

async def get_or_create_driver(company_id: int, name: str) -> Driver:
    async with SessionLocal() as db:
        res = await db.execute(select(Driver).where(Driver.company_id == company_id, Driver.name == name))
        driver = res.scalar_one_or_none()
        if driver:
            return driver
        driver = Driver(company_id=company_id, name=name)
        db.add(driver)
        await db.commit()
        await db.refresh(driver)
        return driver

async def create_trip(company_id: int, driver_id: int, notes: str | None) -> Trip:
    async with SessionLocal() as db:
        trip = Trip(company_id=company_id, driver_id=driver_id, notes=notes)
        db.add(trip)
        await db.commit()
        await db.refresh(trip)
        return trip

async def add_telemetry(t: dict) -> None:
    async with SessionLocal() as db:
        row = Telemetry(**t)
        db.add(row)
        await db.commit()