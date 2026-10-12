from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

CLIENT_COLUMNS = "id, slug, name, db_name, created_at, updated_at, deleted_at"


def create_client(db: Session, *, slug: str, name: str, db_name: str) -> dict[str, object] | None:
    try:
        created = db.execute(
            text(
                f"""
                INSERT INTO clients (slug, name, db_name)
                VALUES (:slug, :name, :db_name)
                RETURNING {CLIENT_COLUMNS}
                """
            ),
            {"slug": slug, "name": name, "db_name": db_name},
        ).mappings().one()
        db.commit()
        return dict(created)
    except IntegrityError:
        db.rollback()
        return None


def list_clients(db: Session) -> list[dict[str, object]]:
    rows = db.execute(
        text(
            f"""
            SELECT {CLIENT_COLUMNS}
            FROM clients
            WHERE deleted_at IS NULL
            ORDER BY created_at DESC, id DESC
            """
        )
    ).mappings().all()
    return [dict(row) for row in rows]


def get_client_by_id(db: Session, client_id: UUID) -> dict[str, object] | None:
    row = db.execute(
        text(
            f"""
            SELECT {CLIENT_COLUMNS}
            FROM clients
            WHERE id = :client_id
              AND deleted_at IS NULL
            """
        ),
        {"client_id": client_id},
    ).mappings().first()
    return None if row is None else dict(row)


def get_client_by_slug(db: Session, slug: str) -> dict[str, object] | None:
    row = db.execute(
        text(
            f"""
            SELECT {CLIENT_COLUMNS}
            FROM clients
            WHERE slug = :slug
              AND deleted_at IS NULL
            """
        ),
        {"slug": slug},
    ).mappings().first()
    return None if row is None else dict(row)


def soft_delete_client(db: Session, client_id: UUID) -> bool:
    try:
        deleted = db.execute(
            text(
                """
                UPDATE clients
                SET deleted_at = :deleted_at
                WHERE id = :client_id
                  AND deleted_at IS NULL
                RETURNING id
                """
            ),
            {"client_id": client_id, "deleted_at": datetime.now(timezone.utc)},
        ).first()

        if deleted is None:
            db.rollback()
            return False

        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
