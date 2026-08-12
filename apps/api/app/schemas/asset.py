import uuid

from pydantic import BaseModel, ConfigDict


class AssetCreate(BaseModel):
    name: str
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    electrical_properties: dict = {}
    mechanical_properties: dict = {}
    thermal_properties: dict = {}
    geometry: dict = {}
    simulation_properties: dict = {}
    twin_confidence: dict = {}


class AssetOut(AssetCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
