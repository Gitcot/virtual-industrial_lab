import uuid

from pydantic import BaseModel, ConfigDict


class MotorSessionCreate(BaseModel):
    asset_id: uuid.UUID | None = None
    # plaque signalétique optionnelle; si absente, valeurs par défaut du moteur pédagogique
    rated_voltage_v: float | None = None
    rated_current_a: float | None = None
    rated_power_kw: float | None = None


class MotorSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_id: uuid.UUID | None
    state: str
    elapsed_in_state_s: float
    simulated_temp_c: float
    current_a: float
    voltage_v: float
    fault_active: str | None


class StartRequest(BaseModel):
    mode: str  # "direct" | "star_delta"


class FaultRequest(BaseModel):
    fault_type: str  # "thermal_overload" | "phase_loss"


class TickRequest(BaseModel):
    dt_seconds: float = 1.0
