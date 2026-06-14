from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime
from src.db.database import Base

class DeviceTelemetry(Base):
    __tablename__ = "device_telemetry"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    sensor_id = Column(String(50), nullable=False, index=True)
    power_w = Column(Float, nullable=False)
    voltage_v = Column(Float, nullable=False)
    total_energy_kwh = Column(Float, nullable=True)


class DevicePrediction(Base):
    __tablename__ = "device_monthly_predictions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.now())
    sensor_id = Column(String(100), nullable=False, index=True)           
    predicted_spend_next_30d = Column(Float, nullable=False)             