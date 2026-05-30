from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "stock_agent"
    postgres_user: str = "stock_agent"
    postgres_password: str = "stock_agent"
    database_url: str | None = None

    news_api_key: str | None = None
    fred_api_key: str | None = None
    dart_api_key: str | None = None
    embedding_model: str = "bge-m3"
    embedding_dimensions: int = 1024
    langsmith_tracing: bool = False
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_api_key: str | None = None
    langsmith_project: str = "stock-agent-local"
    glm_api_key: str | None = None
    glm_base_url: str = "https://api.z.ai/api/paas/v4"
    glm_model: str = "glm-4.5-flash"
    glm_timeout_seconds: int = 30

    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "google/gemini-flash-1.5"
    openrouter_timeout_seconds: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
