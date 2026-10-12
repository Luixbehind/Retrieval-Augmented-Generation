# RAG

Base inicial do projeto com FastAPI, SQLAlchemy, PostgreSQL e Poetry.

## Execução com Docker

1. Copie `.env.example` para `.env`.
2. Ajuste `DATABASE_URL` para o uso local do Alembic e `DATABASE_URL_DOCKER` para a conexão interna do container com o serviço `db`.
3. Se quiser sobrescrever os modelos locais, ajuste `OLLAMA_BASE_URL`, `LLM_MODEL` e `EMBEDDING_MODEL`.
4. Suba a stack completa com `docker compose up --build`.
5. O Ollama ficará disponível em `http://localhost:11434`.
6. A API ficará disponível em `http://localhost:8000`.
7. A documentação Swagger ficará em `http://localhost:8000/docs`.

## Execução local

1. Copie `.env.example` para `.env`.
2. Ajuste `DATABASE_URL` para apontar para o PostgreSQL local.
3. Rode `poetry install`.
4. Inicie a API com `poetry run start`.

## Scraping da LGPD (Planalto)

Para capturar o texto da LGPD removendo trechos riscados da página oficial:

1. Rode `poetry run scrape-lgpd`.
2. Os arquivos serão gerados em `data/legal/lgpd/`:
	- `lgpd_clean.txt` (texto limpo)
	- `lgpd_clean_native.txt` (texto nativo para uso da LLM)
	- `lgpd_clean.pdf` (PDF do texto limpo)

Também é possível customizar:

`poetry run scrape-lgpd --url "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm" --output-dir "data/legal/lgpd"`

