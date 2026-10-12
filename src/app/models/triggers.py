from __future__ import annotations

from alembic_utils.pg_extension import PGExtension
from alembic_utils.pg_function import PGFunction
from alembic_utils.pg_trigger import PGTrigger


update_tsv_fn = PGFunction(
    schema="public",
    signature="update_tsv()",
    definition="""
RETURNS trigger AS $$
BEGIN
  NEW.tsv := to_tsvector('portuguese', coalesce(NEW.content, ''));
  RETURN NEW;
END
$$ LANGUAGE plpgsql
""",
)


set_updated_at_fn = PGFunction(
    schema="public",
    signature="set_updated_at()",
    definition="""
RETURNS trigger AS $$
BEGIN
  NEW.updated_at := NOW();
  RETURN NEW;
END
$$ LANGUAGE plpgsql
""",
)


tsv_legal_update_trigger = PGTrigger(
    schema="public",
    signature="tsv_legal_update",
    on_entity="public.legal_chunks",
    definition="""
BEFORE INSERT OR UPDATE ON legal_chunks
FOR EACH ROW EXECUTE FUNCTION update_tsv();
""",
)


legal_documents_updated_at_trigger = PGTrigger(
    schema="public",
    signature="trg_legal_documents_updated_at",
    on_entity="public.legal_documents",
    definition="""
BEFORE UPDATE ON legal_documents
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
""",
)


legal_chunks_updated_at_trigger = PGTrigger(
    schema="public",
    signature="trg_legal_chunks_updated_at",
    on_entity="public.legal_chunks",
    definition="""
BEFORE UPDATE ON legal_chunks
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
""",
)


rag_queries_updated_at_trigger = PGTrigger(
    schema="public",
    signature="trg_rag_queries_updated_at",
    on_entity="public.rag_queries",
    definition="""
BEFORE UPDATE ON rag_queries
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
""",
)


vector_extension = PGExtension(schema="public", signature="vector")
pgcrypto_extension = PGExtension(schema="public", signature="pgcrypto")


DB_TRIGGER_ENTITIES = [
    vector_extension,
    pgcrypto_extension,
    update_tsv_fn,
    set_updated_at_fn,
    tsv_legal_update_trigger,
    legal_documents_updated_at_trigger,
    legal_chunks_updated_at_trigger,
    rag_queries_updated_at_trigger,
]
