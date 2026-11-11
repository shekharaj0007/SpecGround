from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
LOCAL_SQLITE = f"sqlite:///{(ROOT / 'data' / 'specground.db').as_posix()}"


def _placeholder_key(key: str) -> bool:
    lowered = (key or "").strip().lower()
    if not lowered:
        return True
    return "your-key" in lowered or lowered.endswith("here") or "placeholder" in lowered


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    anthropic_chat_model: str = "claude-sonnet-4-5"
    anthropic_guard_model: str = "claude-haiku-4-5"

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o"
    openai_guard_model: str = "gpt-4o-mini"
    openai_embed_model: str = "text-embedding-3-small"
    embedding_dim: int = 384

    database_url: str = LOCAL_SQLITE
    upload_dir: str = str(ROOT / "data" / "uploads")
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    static_dir: str = ""

    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def _local_database_default(self) -> "Settings":
        # Unset or blank DATABASE_URL stays on the local SQLite file so uvicorn
        # can boot on Windows when Postgres is not installed.
        if not (self.database_url or "").strip():
            self.database_url = LOCAL_SQLITE
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def resolved_anthropic_key(self) -> str:
        if self.anthropic_api_key.startswith("sk-ant-"):
            return self.anthropic_api_key
        if self.openai_api_key.startswith("sk-ant-"):
            return self.openai_api_key
        return self.anthropic_api_key.strip()

    @property
    def anthropic_configured(self) -> bool:
        key = self.resolved_anthropic_key
        return key.startswith("sk-ant-") and not _placeholder_key(key)

    @property
    def using_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


settings = Settings()  # reloaded from .env on process start
