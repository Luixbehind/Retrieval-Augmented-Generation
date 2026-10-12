from __future__ import annotations

import re

from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text

from app.core.config import settings

DB_NAME_PATTERN = re.compile(r"^[a-z0-9_]{1,63}$")


def build_tenant_db_name(slug: str) -> str:
    db_name = f"tenant_{slug.replace('-', '_')}"
    if not DB_NAME_PATTERN.match(db_name):
        raise ValueError(f"Invalid tenant database name derived from slug: {slug!r}")
    return db_name


def create_tenant_database(db_name: str) -> None:
    if not DB_NAME_PATTERN.match(db_name):
        raise ValueError(f"Invalid tenant database name: {db_name!r}")

    maintenance_engine = create_engine(
        settings.get_maintenance_database_url(),
        isolation_level="AUTOCOMMIT",
    )
    try:
        with maintenance_engine.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        maintenance_engine.dispose()

    tenant_engine = create_engine(settings.build_database_url(db_name), isolation_level="AUTOCOMMIT")
    try:
        with tenant_engine.connect() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    finally:
        tenant_engine.dispose()


def run_tenant_migrations(database_url: str) -> None:
    cfg = Config("alembic.ini")
    cfg.attributes["engine_url"] = database_url
    command.upgrade(cfg, "head")
