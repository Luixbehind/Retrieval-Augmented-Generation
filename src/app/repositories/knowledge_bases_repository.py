from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


KB_COLUMNS = (
    "id, name, description, type, config, status, golden_dataset_status, golden_dataset_error_message, "
    "created_at, updated_at, deleted_at"
)


def create_knowledge_base(
    db: Session,
    *,
    name: str,
    description: str | None,
    kb_type: str | None,
) -> dict[str, object]:
    try:
        created = db.execute(
            text(
                f"""
                INSERT INTO knowledge_bases (name, description, type)
                VALUES (:name, :description, :kb_type)
                RETURNING {KB_COLUMNS}
                """
            ),
            {
                "name": name,
                "description": description,
                "kb_type": kb_type,
            },
        ).mappings().one()

        db.commit()
        return dict(created)
    except Exception:
        db.rollback()
        raise


def update_knowledge_base(
    db: Session,
    *,
    knowledge_base_id: UUID,
    update_data: dict[str, object],
) -> dict[str, object] | None:
    allowed_fields = {"name", "description", "config"}
    filtered = {key: value for key, value in update_data.items() if key in allowed_fields}

    if not filtered:
        return get_knowledge_base_by_id(db, knowledge_base_id)

    if "config" in filtered:
        filtered["config"] = json.dumps(filtered["config"])

    set_parts = [
        f"{field} = CAST(:{field} AS json)" if field == "config" else f"{field} = :{field}"
        for field in filtered
    ]
    params = {**filtered, "knowledge_base_id": knowledge_base_id}

    try:
        updated = db.execute(
            text(
                f"""
                UPDATE knowledge_bases
                SET {", ".join(set_parts)}
                WHERE id = :knowledge_base_id
                  AND deleted_at IS NULL
                RETURNING {KB_COLUMNS}
                """
            ),
            params,
        ).mappings().first()

        if updated is None:
            db.rollback()
            return None

        db.commit()
        return dict(updated)
    except Exception:
        db.rollback()
        raise


def get_knowledge_base_by_id(db: Session, knowledge_base_id: UUID) -> dict[str, object] | None:
    row = db.execute(
        text(
            f"""
            SELECT {KB_COLUMNS}
            FROM knowledge_bases
            WHERE id = :knowledge_base_id
              AND deleted_at IS NULL
            """
        ),
        {"knowledge_base_id": knowledge_base_id},
    ).mappings().first()
    return None if row is None else dict(row)


def knowledge_base_exists(db: Session, knowledge_base_id: UUID) -> bool:
    row = db.execute(
        text("SELECT 1 FROM knowledge_bases WHERE id = :knowledge_base_id AND deleted_at IS NULL"),
        {"knowledge_base_id": knowledge_base_id},
    ).first()
    return row is not None


def is_knowledge_base_archived(db: Session, knowledge_base_id: UUID) -> bool:
    row = db.execute(
        text("SELECT 1 FROM knowledge_bases WHERE id = :knowledge_base_id AND status = 'ARCHIVED'"),
        {"knowledge_base_id": knowledge_base_id},
    ).first()
    return row is not None


def mark_golden_dataset_pending(db: Session, *, knowledge_base_id: UUID) -> None:
    db.execute(
        text(
            """
            UPDATE knowledge_bases
            SET golden_dataset_status = 'PENDING', golden_dataset_error_message = NULL
            WHERE id = :knowledge_base_id
            """
        ),
        {"knowledge_base_id": knowledge_base_id},
    )
    db.commit()


def mark_golden_dataset_completed(db: Session, *, knowledge_base_id: UUID) -> None:
    db.execute(
        text(
            """
            UPDATE knowledge_bases
            SET golden_dataset_status = 'COMPLETED', golden_dataset_error_message = NULL
            WHERE id = :knowledge_base_id
            """
        ),
        {"knowledge_base_id": knowledge_base_id},
    )
    db.commit()


def mark_golden_dataset_failed(db: Session, *, knowledge_base_id: UUID, error_message: str) -> None:
    db.execute(
        text(
            """
            UPDATE knowledge_bases
            SET golden_dataset_status = 'FAILED', golden_dataset_error_message = :error_message
            WHERE id = :knowledge_base_id
            """
        ),
        {"knowledge_base_id": knowledge_base_id, "error_message": error_message[:2000]},
    )
    db.commit()


def list_knowledge_bases(db: Session) -> list[dict[str, object]]:
    rows = db.execute(
        text(
            f"""
            SELECT {KB_COLUMNS}
            FROM knowledge_bases
            WHERE deleted_at IS NULL
            ORDER BY created_at DESC, id DESC
            """
        )
    ).mappings().all()
    return [dict(row) for row in rows]


def mark_edited_if_published(db: Session, *, knowledge_base_id: UUID) -> None:
    """Move uma knowledge base de PUBLISHED para EDITED quando seu conteúdo publicado recebe uma alteração pendente."""
    db.execute(
        text(
            """
            UPDATE knowledge_bases
            SET status = 'EDITED'
            WHERE id = :knowledge_base_id AND status = 'PUBLISHED'
            """
        ),
        {"knowledge_base_id": knowledge_base_id},
    )


class NothingToPublishError(Exception):
    """Raised when a knowledge base has no EDIT-environment content to promote."""


def publish_knowledge_base(db: Session, *, knowledge_base_id: UUID) -> dict[str, object] | None:
    """
    Promove o conteúdo em edição (EDIT) de uma knowledge base para produção (PUBLISHED),
    descartando (soft delete) o conteúdo PUBLISHED anterior.
    """
    try:
        kb = db.execute(
            text(
                f"""
                SELECT {KB_COLUMNS}
                FROM knowledge_bases
                WHERE id = :knowledge_base_id AND deleted_at IS NULL
                """
            ),
            {"knowledge_base_id": knowledge_base_id},
        ).mappings().first()

        if kb is None:
            db.rollback()
            return None

        has_edit_content = db.execute(
            text(
                """
                SELECT 1 FROM legal_documents
                WHERE knowledge_base_id = :knowledge_base_id AND environment = 'EDIT' AND deleted_at IS NULL
                LIMIT 1
                """
            ),
            {"knowledge_base_id": knowledge_base_id},
        ).first()

        if has_edit_content is None:
            db.rollback()
            raise NothingToPublishError("Knowledge base has no pending changes to publish")

        now = datetime.now(timezone.utc)

        db.execute(
            text(
                """
                UPDATE legal_chunks
                SET deleted_at = :now
                WHERE deleted_at IS NULL
                  AND document_id IN (
                      SELECT id FROM legal_documents
                      WHERE knowledge_base_id = :knowledge_base_id AND environment = 'PUBLISHED' AND deleted_at IS NULL
                  )
                """
            ),
            {"now": now, "knowledge_base_id": knowledge_base_id},
        )
        db.execute(
            text(
                """
                UPDATE legal_documents
                SET deleted_at = :now
                WHERE knowledge_base_id = :knowledge_base_id AND environment = 'PUBLISHED' AND deleted_at IS NULL
                """
            ),
            {"now": now, "knowledge_base_id": knowledge_base_id},
        )

        db.execute(
            text(
                """
                UPDATE legal_documents
                SET environment = 'PUBLISHED'
                WHERE knowledge_base_id = :knowledge_base_id AND environment = 'EDIT' AND deleted_at IS NULL
                """
            ),
            {"knowledge_base_id": knowledge_base_id},
        )

        updated = db.execute(
            text(
                f"""
                UPDATE knowledge_bases
                SET status = 'PUBLISHED'
                WHERE id = :knowledge_base_id
                RETURNING {KB_COLUMNS}
                """
            ),
            {"knowledge_base_id": knowledge_base_id},
        ).mappings().one()

        db.commit()
        return dict(updated)
    except NothingToPublishError:
        raise
    except Exception:
        db.rollback()
        raise


def soft_delete_knowledge_base(db: Session, *, knowledge_base_id: UUID) -> bool:
    try:
        deleted = db.execute(
            text(
                """
                UPDATE knowledge_bases
                SET deleted_at = :deleted_at
                WHERE id = :knowledge_base_id
                  AND deleted_at IS NULL
                RETURNING id
                """
            ),
            {"knowledge_base_id": knowledge_base_id, "deleted_at": datetime.now(timezone.utc)},
        ).first()

        if deleted is None:
            db.rollback()
            return False

        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
