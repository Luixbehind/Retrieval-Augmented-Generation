from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.control_db import get_control_db
from app.repositories.clients_repository import get_client_by_slug

_tenant_engines: dict[str, Engine] = {}


def get_tenant_engine(db_name: str) -> Engine:
    engine = _tenant_engines.get(db_name)
    if engine is None:
        engine = create_engine(settings.build_database_url(db_name), pool_pre_ping=True)
        _tenant_engines[db_name] = engine
    return engine


def get_tenant_session_factory(db_name: str) -> sessionmaker[Session]:
    engine = get_tenant_engine(db_name)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)


def resolve_tenant_client(x_client_slug: str, control_db: Session) -> dict:
    client = get_client_by_slug(control_db, x_client_slug)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


def get_tenant_db(
    x_client_slug: str = Header(alias="X-Client-Slug"),
    control_db: Session = Depends(get_control_db),
) -> Iterator[Session]:
    client = resolve_tenant_client(x_client_slug, control_db)

    session_factory = get_tenant_session_factory(client["db_name"])
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def get_tenant_database_url(
    x_client_slug: str = Header(alias="X-Client-Slug"),
    control_db: Session = Depends(get_control_db),
) -> str:
    client = resolve_tenant_client(x_client_slug, control_db)
    return settings.build_database_url(client["db_name"])
