"""Configuration managed by pydantic-settings."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class PipelineSettings(BaseSettings):
    """Pipeline and LLM configuration."""

    google_api_key: str
    supabase_url: str
    supabase_service_role_key: str | None = None
    supabase_anon_key: str | None = None

    # Gemini embeddings (vector index step)
    model_embed: str = "gemini-embedding-001"

    # Ollama — markdown → JSON (parse_problems / parse_solutions)
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1:8b"

    # Nougat PDF → markdown (local only; weights downloaded from Hugging Face Hub on first run)
    nougat_model_id: str = "facebook/nougat-small"
    # auto | cuda | cuda:N | mps | cpu — ``auto`` picks CUDA, then Apple MPS, then CPU
    nougat_device: str = "auto"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = PipelineSettings()
