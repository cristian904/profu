"""Configuration managed by pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class PipelineSettings(BaseSettings):
    """Pipeline and LLM configuration."""

    google_api_key: str
    supabase_url: str
    supabase_service_role_key: str | None = None
    supabase_anon_key: str | None = None

    model_vision: str = "gemini-2.5-flash"
    model_structured: str = "gemini-2.5-flash"
    model_fix_identify: str = "gemini-2.5-flash"
    model_fix_repair: str = "gemini-2.5-flash-lite-preview-02-05" # Defaulting to the latest lite preview 
    model_embed: str = "gemini-embedding-001"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = PipelineSettings()
