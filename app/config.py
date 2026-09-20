from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    ollama_api_key: str | None = None
    # Temporary fallback lets existing local setups migrate without exposing or
    # rewriting their secret automatically. Prefer OLLAMA_API_KEY going forward.
    nvidia_api_key: str | None = None
    nemotron_model: str = "nemotron-3-ultra:cloud"
    mock_mode: bool = True
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"
    max_file_size_mb: int = 10
    data_dir: Path = Path("data")

    @property
    def provider_api_key(self) -> str | None:
        return self.ollama_api_key or self.nvidia_api_key

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
