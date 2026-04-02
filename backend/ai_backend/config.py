"""
Application settings loaded from environment and .env (repo root).
Uses pydantic-settings; .env is loaded from current working directory (run from repo root).
"""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Optional: Supabase for /solve-problem/suggest-problem (vector search) and quota
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    @field_validator("supabase_jwt_secret", mode="before")
    @classmethod
    def strip_jwt_secret(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

    # Solve-problem monthly quota (count from account creation); 0 = disabled
    solve_monthly_quota_threshold: int = 0

    # CORS: comma-separated origins; empty = allow any origin with credentials disabled (Bearer auth)
    cors_allow_origins: str = ""

    @property
    def supabase_key(self) -> str:
        """Prefer service role key; fall back to anon key."""
        return self.supabase_service_role_key or self.supabase_anon_key


# Single instance; load once at import (reads .env from cwd)
settings = Settings()
