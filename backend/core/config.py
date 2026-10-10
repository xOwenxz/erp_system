"""Configurações centralizadas da aplicação (lidas de variáveis de ambiente / .env)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ERP Básico"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"

    # Troque para PostgreSQL em produção, ex.: postgresql+psycopg://user:pass@host/db
    database_url: str = f"sqlite:///{(BASE_DIR / 'data' / 'erp.db').as_posix()}"
    database_echo: bool = False

    cors_origins: list[str] = ["*"]

    # Limites para leitura de planilhas
    excel_max_rows: int = 10_000
    excel_max_file_mb: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
