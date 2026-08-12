"""
Types de colonnes portables entre PostgreSQL (serveur) et SQLite (client
offline-first), pour que le même modèle SQLAlchemy fonctionne des deux côtés
sans dupliquer les définitions.
"""
import uuid

from sqlalchemy import CHAR, JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID


class PortableUUID(TypeDecorator):
    """Stocke un UUID natif sur Postgres, une chaîne CHAR(36) sur SQLite."""

    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        if not isinstance(value, uuid.UUID):
            return str(uuid.UUID(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


PortableJSON = JSON().with_variant(JSONB, "postgresql")
