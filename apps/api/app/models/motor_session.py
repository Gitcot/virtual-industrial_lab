import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import PortableJSON, PortableUUID


class MotorSession(Base):
    """
    Persiste l'état d'une session de simulation moteur (Phase 4) entre les
    appels API. Une session appartient à un utilisateur et peut référencer
    un Asset (plaque signalétique réelle, futur Digital Twin).
    """

    __tablename__ = "motor_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, ForeignKey("users.id"), nullable=False
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        PortableUUID, ForeignKey("assets.id"), nullable=True
    )

    state: Mapped[str] = mapped_column(String(50), default="stopped")
    elapsed_in_state_s: Mapped[float] = mapped_column(Float, default=0.0)
    simulated_temp_c: Mapped[float] = mapped_column(Float, default=25.0)
    current_a: Mapped[float] = mapped_column(Float, default=0.0)
    voltage_v: Mapped[float] = mapped_column(Float, default=0.0)
    fault_active: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # plaque signalétique simplifiée utilisée pour cette session (copie des
    # MotorParameters au moment de la création, pour rester indépendant si
    # l'Asset lié change ensuite)
    motor_parameters: Mapped[dict] = mapped_column(PortableJSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
