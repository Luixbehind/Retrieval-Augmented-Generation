from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RAG API"
    api_v1_prefix: str = "/api/v1"
    # Backward compatibility: if set, this value has priority (used by manual/local Alembic runs).
    database_url: str | None = None
    supabase_db_url: str | None = None

    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_maintenance_db: str = "postgres"
    control_db_name: str = "rag_control"

    ollama_base_url: str = "http://ollama:11434"
    llm_model: str = "mistral"
    embedding_model: str = "bge-m3"
    # Modelo usado como LLM-judge nas avaliações RAGAS. Se não definido, cai no mesmo llm_model
    # de produção — mas usar um modelo diferente evita o viés do modelo se autoavaliar.
    ragas_judge_model: str | None = None
    report_download_api_key: str | None = None
    report_storage_dir: str = "data/reports"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    cors_allow_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def get_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        if self.supabase_db_url:
            return self.supabase_db_url

        raise ValueError("Defina DATABASE_URL ou SUPABASE_DB_URL com uma conexão PostgreSQL válida.")

    def build_database_url(self, db_name: str) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{db_name}"
        )

    def get_control_database_url(self) -> str:
        return self.build_database_url(self.control_db_name)

    def get_maintenance_database_url(self) -> str:
        return self.build_database_url(self.postgres_maintenance_db)


settings = Settings()
