from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RAG API"
    api_v1_prefix: str = "/api/v1"
    # Backward compatibility: if set, this value has priority.
    database_url: str | None = None
    supabase_db_url: str | None = None
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def get_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        if self.supabase_db_url:
            return self.supabase_db_url

        raise ValueError("Defina DATABASE_URL ou SUPABASE_DB_URL com uma conexão PostgreSQL válida.")


settings = Settings()
