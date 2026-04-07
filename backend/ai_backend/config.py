"""
Application settings loaded from environment and .env (repo root).
Uses pydantic-settings; .env is loaded from current working directory (run from repo root).
"""

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _strip_quotes(v: str) -> str:
    """Strip surrounding single/double quotes and whitespace from a string."""
    s = v.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1].strip()
    return s


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini (required for LLM, OCR, embeddings)
    google_api_key: str = ""
    # Gemini model name for chat and vision (e.g. gemini-2.0-flash)
    gemini_model: str = "gemini-2.0-flash"

    # Optional: PostgreSQL async URL for future use
    database_url: str = ""

    # Optional: Supabase for /rag/suggest-problem (vector search) and quota
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    @field_validator("supabase_jwt_secret", mode="before")
    @classmethod
    def strip_jwt_secret(cls, v: str) -> str:
        """Strip whitespace from JWT secret (common copy-paste artifact)."""
        if isinstance(v, str):
            return v.strip()
        return v

    # Solve-problem monthly quota (count from account creation); 0 = disabled
    solve_monthly_quota_threshold: int = 0

    # Langfuse tracing (optional; tracing disabled when keys are empty).
    # Deployment (local vs cloud) is controlled solely by these env vars — no code changes needed.
    # Accepted env var names: LANGFUSE_HOST or LANGFUSE_BASE_URL (same effect).
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    # Primary: set via LANGFUSE_HOST. If absent, LANGFUSE_BASE_URL is used (see model_validator below).
    langfuse_host: str = ""
    # Alternative name accepted by the Flutter client and docker-compose files.
    langfuse_base_url: str = ""

    @field_validator("langfuse_public_key", "langfuse_secret_key", "langfuse_host", "langfuse_base_url", mode="before")
    @classmethod
    def strip_langfuse_string_quotes(cls, v: object) -> object:
        """Strip surrounding quotes from .env values (common copy-paste mistake)."""
        if not isinstance(v, str):
            return v
        return _strip_quotes(v)

    @model_validator(mode="after")
    def resolve_langfuse_host(self) -> "Settings":
        """
        Pick the effective Langfuse host after all fields are resolved by pydantic-settings.

        Priority: LANGFUSE_HOST > LANGFUSE_BASE_URL > https://cloud.langfuse.com (default).
        Using a model_validator (not field_validator) ensures both fields are fully loaded
        from the .env file before the decision is made.
        """
        if self.langfuse_host:
            self.langfuse_host = self.langfuse_host.rstrip("/")
        elif self.langfuse_base_url:
            self.langfuse_host = self.langfuse_base_url.rstrip("/")
        else:
            self.langfuse_host = "https://cloud.langfuse.com"
        return self

    # CORS: comma-separated origins; empty = allow any origin with credentials disabled (Bearer auth)
    cors_allow_origins: str = ""

    @property
    def supabase_key(self) -> str:
        """Prefer service role key; fall back to anon key."""
        return self.supabase_service_role_key or self.supabase_anon_key


# Single instance; load once at import (reads .env from cwd)
settings = Settings()
