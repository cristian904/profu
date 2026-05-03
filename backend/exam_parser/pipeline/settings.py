"""Configuration managed by pydantic-settings."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

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
    ollama_model: str = "qwen2.5-coder:7b"

    # Nougat PDF → markdown (local only; weights downloaded from Hugging Face Hub on first run)
    nougat_model_id: str = "facebook/nougat-base"
    # auto | cuda | cuda:N | mps | cpu — ``cuda`` enforces GPU and fails fast if unavailable
    nougat_device: str = "cuda"
    # Per-PDF extraction timeout in seconds. Prevents one stuck file from blocking the step.
    nougat_pdf_timeout_seconds: int = 120

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_pipeline_settings() -> PipelineSettings:
    """
    Load settings once per process.

    Kept separate from module import so tests can import ``PipelineSettings``
    without required environment variables being set.
    """
    return PipelineSettings()


class _LazyPipelineSettings:
    """Proxy that defers ``PipelineSettings()`` until first attribute access."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_pipeline_settings(), name)


settings = _LazyPipelineSettings()
