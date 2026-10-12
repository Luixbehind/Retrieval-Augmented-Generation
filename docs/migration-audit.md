# Auditoria de migrações do projeto

## Objetivo

Manter a trilha histórica do Alembic como referência, mas alinhar a aplicação ao fluxo atual de compliance LGPD:

- Entrada: schema SQL + termo de compromisso
- Comparação: com a LGPD
- Saída: relatório estruturado
- Fonte de verdade: relatório gerado
- Persistência: `legal_documents` + `legal_chunks` + `embedding` em PGVector

## Migrações essenciais para o fluxo atual

Essas migrações são as que sustentam o modelo mínimo da solução:

1. `f140aee465ae_create_legal_documents_and_chunks_tables.py`
   - Cria `legal_documents` e `legal_chunks`
   - Central para salvar o relatório e os chunks vetorizados

2. `e95aea0524f1_add_trigger_entities_from_models.py`
   - Cria funções e triggers para `tsv` e `updated_at`
   - Essencial para busca textual e atualização automática

3. `cfb2253bd3f9_add_document_processing_status.py`
   - Adiciona `processing_status` para `knowledge_documents`
   - Útil se você quiser manter upload/processamento de documentos

4. `bf8d3ea53231_add_json_to_document_type_enum.py`
   - Permite receber arquivos JSON
   - Útil para schema/arquivo estruturado

5. `205d5fabfd22_create_knowledge_bases_and_link_.py`
   - Cria `knowledge_bases`
   - Relevante apenas se o sistema manter múltiplos workspaces/knowledge bases

6. `9125653e686d_create_knowledge_documents_table.py`
   - Cria `knowledge_documents`
   - Dependente do fluxo de upload de documentos

## Migrações históricas / legadas

Essas migrações pertencem ao RAG genérico e não são essenciais para o relatório LGPD como fonte única:

- `5fbc980134aa_create_documents_table.py`
- `b7d3c2a91e44_rename_documents_to_knowlegde_embeddings.py`
- `2baee7d8555c_add_fk_from_knowlegde_embeddings_to_.py`
- `78a7dd234dce_add_kb_versioning_and_rag_comparison_.py`
- `60862e56ec28_create_rag_queries_table.py`
- `1ccbf05ec1df_add_rag_queries_updated_at_trigger.py`
- `6fde4286ca3c_remove_is_active_from_knowledge_bases.py`
- `g156de8f5a2g_add_config_to_knowledge_bases.py`

## Recomendação aplicada

Para evitar quebrar o histórico de migrações, mantemos essas migrações na árvore do Alembic como referência histórica, mas a aplicação ativa foi alignada para o fluxo report-only:

- `legal_documents` e `legal_chunks` são a base da verdade
- os relatórios são indexados em PGVector
- os schemas e termos brutos não são fonte da RAG
- o restante do sistema de knowledge base/versioning ficou em segundo plano

## Regra de decisão

Se a tabela ou migração não alimenta diretamente:

- o relatório LGPD final
- os chunks do relatório
- a busca vetorial do relatório

então ela é considerada legacy para o escopo atual.
