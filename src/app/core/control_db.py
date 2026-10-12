from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

control_engine = create_engine(settings.get_control_database_url(), pool_pre_ping=True)
ControlSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=control_engine, class_=Session)


def get_control_db() -> Iterator[Session]:
    db = ControlSessionLocal()
    try:
        yield db
    finally:
        db.close()
