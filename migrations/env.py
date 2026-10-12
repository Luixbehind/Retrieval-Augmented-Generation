from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from alembic_utils.replaceable_entity import register_entities
from sqlalchemy import engine_from_config, pool

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from app.core.config import settings
from app.core.database import Base
import app.models
from app.models.triggers import DB_TRIGGER_ENTITIES

register_entities(DB_TRIGGER_ENTITIES)

config = context.config
if config.config_file_name is not None:
    # disable_existing_loggers=False: this env.py can run in-process (tenant provisioning
    # calls alembic.command.upgrade from within the running FastAPI app), and fileConfig's
    # default would otherwise silently kill uvicorn's and the app's loggers for the rest
    # of the process lifetime.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata
db_url = config.attributes.get("engine_url") or settings.get_database_url()


def run_migrations_offline() -> None:
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        {"sqlalchemy.url": db_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
