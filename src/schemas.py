from datetime import datetime
from pydantic import BaseModel, Field

class TelemetryCreate(BaseModel):
    sensor_id: str = Field(..., example="sensor.shelly_fridge_kitchen", description="Unique identifier of the sensor")
    power_w: float = Field(..., gte=0.0, example=120.5, description="Current instantaneous power in Watts")
    voltage_v: float = Field(..., gte=0.0, example=230.0, description="Current voltage in Volts")
    total_energy_kwh: float = Field(..., gte=0.0, example=452.12, description="Total accumulated energy in kWh")

class TelemetryResponse(BaseModel):
    id: int
    sensor_id: str
    power_w: float
    voltage_v: float
    total_energy_kwh: float
    timestamp: datetime

    class Config:
        from_attributes = True

class PredictionResponse(BaseModel):
    sensor_id: str
    predicted_spend_next_30d: float
    calculated_at: datetime

class EnergyReportResponse(BaseModel):
    status: str = Field(..., description="Status of the energy report ('success' o 'no_data')")
    generated_at: datetime = Field(..., description="Timestamp of the creation of the report")
    report: str = Field(..., description="Content of the report in Markdown format")

class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="Health status of the API ('online' o 'offline')")
    message: str = Field(..., description="Additional information about the health status")
    timestamp: datetime = Field(..., description="Timestamp of the health check response")

class TrainingResponse(BaseModel):
    status: str = Field(..., description="Status of the training process ('started', 'in_progress')")
    message: str = Field(..., description="Additional information about the training status")