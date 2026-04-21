# RAG

Base inicial do projeto com FastAPI, SQLAlchemy, PostgreSQL e Poetry.

## Execução com Docker

1. Copie `.env.example` para `.env`.
2. Ajuste `DATABASE_URL` para o uso local do Alembic e `DATABASE_URL_DOCKER` para a conexão interna do container com o serviço `db`.
3. Suba o PostgreSQL com `docker compose up -d db`.
4. Gere a migration com `poetry run alembic revision --autogenerate -m "create documents table"`.
5. Suba a API com `docker compose up --build api`.
6. A API ficará disponível em `http://localhost:8000`.
7. A documentação Swagger ficará em `http://localhost:8000/docs`.

## Execução local

1. Copie `.env.example` para `.env`.
2. Ajuste `DATABASE_URL` para apontar para o PostgreSQL local.
3. Rode `poetry install`.
4. Inicie a API com `poetry run start`.

