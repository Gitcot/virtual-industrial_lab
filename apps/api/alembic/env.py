from logging.config import fileConfig

from alembic import context
from sqlalchemy import JSON, engine_from_config, pool

from app.core.config import settings
from app.core.database import Base
from app.core.types import PortableUUID
from app import models  # noqa: F401  (assure que tous les modèles sont enregistrés)

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):
    """
    Rend nos types portables (PortableUUID / PortableJSON) comme des appels
    lisibles et correctement importés dans les fichiers de migration, plutôt
    que de laisser Alembic les expanser en code cassé (imports manquants).
    """
    if type_ == "type":
        if isinstance(obj, PortableUUID):
            autogen_context.imports.add("from app.core.types import PortableUUID")
            return "PortableUUID()"
        if isinstance(obj, JSON) and "postgresql" in getattr(obj, "_variant_mapping", {}):
            autogen_context.imports.add("from app.core.types import PortableJSON")
            return "PortableJSON"
    return False


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True,
        dialect_opts={"paramstyle": "named"}, render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, render_item=render_item
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
