"""All settings in one place, read from environment variables (or a local .env file).

Why: the same code runs on your laptop and on Cloud Run. Only the settings change,
and secrets never live in the code.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["local", "dev", "prod"] = "local"
    gcp_project_id: str = "mandap-ai"
    gcp_region: str = "asia-south1"

    # One switch decides how we reach Claude. Changing providers later is one line.
    llm_provider: Literal["anthropic", "vertex"] = "anthropic"
    anthropic_api_key: str = ""

    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
