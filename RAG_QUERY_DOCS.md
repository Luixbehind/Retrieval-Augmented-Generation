# RAG Query - Documentação da Busca Híbrida

## Visão Geral

Implementação de busca híbrida (BM25 + vetorial) com retrieval paralelo de:
- **LGPD**: Busca vetorial pura nos `LegalChunks`
- **Cliente**: Busca híbrida nos `Documents` com pesos configuráveis

## Arquitetura da Query

```
Pergunta
   ↓
Embedding (via Ollama)
   ↓
Retrieval Paralelo
   ├─ LGPD: Vector Search (cosine similarity)
   └─ Cliente: Hybrid Search
      ├─ BM25 (textual com stopwords PT)
      └─ Vector Search (cosine similarity)
   ↓
Merge e Re-rank (com pesos)
   ↓
Top K Results (cortados por config)
   ↓
LLM: Gera resposta final
```

## Endpoints

### POST /queries

Executa uma query RAG com busca híbrida.

**Request:**
```json
{
  "query": "Qual é a Lei Geral de Proteção de Dados?",
  "knowledge_base_version_id": "uuid-opcional"
}
```

**Response:**
```json
{
  "lgpd": [
    {
      "id": "chunk-id",
      "content": "artigo da LGPD",
      "article": "Art. 1",
      "section": "Seção I",
      "score": 0.95,
      "source": "LGPD"
    }
  ],
  "cliente": [
    {
      "id": "doc-id",
      "title": "Documento do Cliente",
      "summary": "Resumo",
      "content": "conteúdo do documento",
      "score": 0.87,
      "source": "Cliente"
    }
  ]
}
```

## Configuração

### Modelo KnowledgeBase

Campo `config` (JSON) com defaults:
```json
{
  "top_k": 10,
  "hybrid_weight_bm25": 0.7,
  "hybrid_weight_vector": 0.3
}
```

**Parâmetros:**
- `top_k`: Número máximo de resultados por fonte
- `hybrid_weight_bm25`: Peso para BM25 na busca híbrida (0-1)
- `hybrid_weight_vector`: Peso para vector search na busca híbrida (0-1)

**Exemplo atualizar config:**
```bash
PATCH /knowledge-bases/{id}
{
  "config": {
    "top_k": 20,
    "hybrid_weight_bm25": 0.6,
    "hybrid_weight_vector": 0.4
  }
}
```

## Stopwords Portugueses

O BM25 remove 100+ stopwords em português para melhorar a relevância:
- Artigos: a, o, os, as
- Preposições: de, em, para, por, com, sem
- Verbos comuns: ser, estar, ter, fazer
- Conectores: e, ou, mas, pois

## Dependências Adicionadas

```toml
rank-bm25 = "^0.2.2"
nltk = "^3.8.1"
```

## Database

### Migration

`migrations/versions/g156de8f5a2g_add_config_to_knowledge_bases.py`

Adiciona coluna `config` JSON ao `knowledge_bases` com default:
```json
{
  "top_k": 10,
  "hybrid_weight_bm25": 0.7,
  "hybrid_weight_vector": 0.3
}
```

## Próximos Passos

1. Implementar LLM response generation usando contexto recuperado
2. Adicionar persistência de queries e respostas em `rag_queries` table
3. Implementar re-ranking adicional com modelos específicos
4. Adicionar suporte a filtering por metadata (date range, source, etc)

## Arquivos Modificados

- `src/app/models/knowledge_base.py` - Adiciona campo `config`
- `src/app/schemas/knowledge_base.py` - Adiciona `config` nos schemas
- `src/app/schemas/rag_query.py` - Novos schemas para query
- `src/app/services/retrieval_service.py` - Lógica de retrieval
- `src/app/api/v1/endpoints/rag_queries.py` - Endpoint `/queries`
- `src/app/api/v1/router.py` - Registra novo endpoint
- `pyproject.toml` - Adiciona dependências
- `migrations/versions/g156de8f5a2g_*.py` - Migration para config
