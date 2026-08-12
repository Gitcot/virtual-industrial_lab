import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import PortableJSON, PortableUUID


class Asset(Base):
    """
    Représente un équipement (ex: moteur asynchrone) et sert de base
    extensible au futur Digital Twin (Phase 12-13).
    Chaque bloc de propriétés est un JSON libre pour rester extensible
    sans migration DB à chaque nouveau paramètre.
    Fonctionne aussi bien sur SQLite (client offline) que Postgres (serveur).
    """

    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID, primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(255), nullable=True)
    model: Mapped[str] = mapped_column(String(255), nullable=True)
    serial_number: Mapped[str] = mapped_column(String(255), nullable=True)

    electrical_properties: Mapped[dict] = mapped_column(PortableJSON, default=dict)
    mechanical_properties: Mapped[dict] = mapped_column(PortableJSON, default=dict)
    thermal_properties: Mapped[dict] = mapped_column(PortableJSON, default=dict)
    geometry: Mapped[dict] = mapped_column(PortableJSON, default=dict)
    simulation_properties: Mapped[dict] = mapped_column(PortableJSON, default=dict)

    # niveau de confiance par paramètre: nominal|mesure|estime|derive|valide
    twin_confidence: Mapped[dict] = mapped_column(PortableJSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
