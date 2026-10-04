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

    # Model names differ slightly between Anthropic and Google. Change here, not in code.
    anthropic_model_fast: str = "claude-haiku-4-5-20251001"
    anthropic_model_smart: str = "claude-sonnet-5-5"
    vertex_model_fast: str = "claude-haiku-4-5@20251001"
    vertex_model_smart: str = "claude-sonnet-5-5"

    usd_to_inr: float = 85.0  # rough rate, only for showing costs in rupees

    # firestore in the cloud; memory for tests and quick local runs
    store_backend: Literal["firestore", "memory"] = "firestore"

    # Knowledge base (RAG). vertex = Google's embedding model; hash = offline stand-in for tests.
    embed_backend: Literal["vertex", "hash"] = "vertex"
    embed_model: str = "gemini-embedding-001"
    embed_dim: int = 768
    embed_regions: str = "asia-south1,us-central1"  # tried in order
    rag_min_score: float = 0.62  # passages less similar than this are not given to the AI

    cors_origins: str = "http://localhost:3000"
    # Also allow our Firebase App Hosting site (address looks like
    # https://mandap-web--mandap-ai.<region>.hosted.app) and any local dev port.
    cors_origin_regex: str = r"https://[a-z0-9-]+--mandap-ai\.[a-z0-9-]+\.hosted\.app|http://localhost:\d+"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
