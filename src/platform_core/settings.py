"""Application settings loaded from environment / .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = Field(default="development")
    app_secret_key: str = Field(default="dev-secret-not-for-production")
    app_host: str = Field(default="127.0.0.1")
    app_port: int = Field(default=8000)

    database_url: str = Field(default="sqlite:///./var/gravity.db")

    log_level: str = Field(default="INFO")

    @property
    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def templates_dir(self) -> Path:
        return Path(__file__).resolve().parent / "web" / "templates"

    @property
    def static_dir(self) -> Path:
        return Path(__file__).resolve().parent / "web" / "static"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
