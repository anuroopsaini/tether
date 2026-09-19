from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    nvidia_api_key: str | None = None
    nemotron_model: str = "nvidia/llama-3.3-nemotron-super-49b-v1"
    mock_mode: bool = True
    allowed_origins: str = "http://localhost:3000"
    max_file_size_mb: int = 10
    data_dir: Path = Path("data")

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
