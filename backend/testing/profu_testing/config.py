"""
Pydantic settings for ``profu_testing``: loads the repo-root ``.env`` when present,
plus process environment. Mirrors variable names used by ``ai_backend`` and the
clarify eval harness.

Environment variables (repo root ``.env``):

- ``GOOGLE_API_KEY``, ``GEMINI_MODEL`` — checklist LLM (Gemini).
- ``API_BASE_URL`` — default API root when ``TESTING_API_BASE_URL`` is unset.
- ``DATABASE_URL`` — optional; reserved for future harness features (not read by ``run`` today).
- ``SUPABASE_*``, ``SOLVE_MONTHLY_QUOTA_THRESHOLD`` — optional; same as backend (harness uses HTTP + JWT only today).
- ``LANGFUSE_PUBLIC_KEY``, ``LANGFUSE_SECRET_KEY``, ``LANGFUSE_BASE_URL`` / ``LANGFUSE_HOST`` — dataset registration.

Harness-specific (often set only in shell or added to ``.env`` manually):

- ``EVAL_JWT`` or ``PROFU_EVAL_BEARER`` — Supabase access token for ``Authorization: Bearer``.
- ``TESTING_API_BASE_URL`` — override API base for the harness.
- ``TESTING_GEMINI_MODEL`` — override Gemini model for checklists only.
- ``PROFU_LANGFUSE_EVAL_DATASET`` — Langfuse dataset name for ``create_dataset_item``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def repo_root() -> Path:
    """
    Resolve monorepo root (directory that contains ``backend/`` and ``.env``).

    Returns:
        Absolute path to the repository root.
    """
    # profu_testing/config.py -> parents[3] = repo root
    return Path(__file__).resolve().parents[3]


def _strip_quotes(value: str) -> str:
    """Strip surrounding single/double quotes and outer whitespace."""
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in "\"'":
        return stripped[1:-1].strip()
    return stripped


def testing_env_files() -> tuple[str, ...] | None:
    """
    Build a tuple of existing ``.env`` paths: repo root first, then cwd.

    Returns:
        Tuple of absolute paths, or ``None`` if no file exists.
    """
    paths: list[str] = []
    root_env = repo_root() / ".env"
    if root_env.is_file():
        paths.append(str(root_env.resolve()))
    try:
        cwd_env = Path(".env").resolve()
    except OSError:
        cwd_env = Path(".env")
    if cwd_env.is_file():
        resolved = str(cwd_env)
        if resolved not in paths:
            paths.append(resolved)
    return tuple(paths) if paths else None


class ProfuTestingSettings(BaseSettings):
    """
    Settings for the ``profu_testing`` package, loaded from env and ``.env`` files.
    """

    model_config = SettingsConfigDict(
        env_file=testing_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Gemini (root .env: GOOGLE_API_KEY, GEMINI_MODEL) ---
    google_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    testing_gemini_model: str = Field(
        default="",
        description="Optional override (TESTING_GEMINI_MODEL) for checklist generation only.",
    )

    # --- API target (root .env: API_BASE_URL; harness: TESTING_API_BASE_URL) ---
    api_base_url: str = Field(
        default="",
        description="Default API root from API_BASE_URL (Flutter/backend convention).",
    )
    testing_api_base_url: str = Field(
        default="",
        description="Override for harness HTTP calls (TESTING_API_BASE_URL).",
    )

    # --- Auth for harness (not always in committed .env; set locally) ---
    eval_jwt: str = Field(
        default="",
        validation_alias=AliasChoices("eval_jwt", "profu_eval_bearer"),
        description="Supabase JWT for EVAL_JWT or PROFU_EVAL_BEARER.",
    )

    # --- Optional DB / Supabase (root .env parity; unused by current run harness) ---
    database_url: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    solve_monthly_quota_threshold: int = 0

    # --- Langfuse (root .env + optional LANGFUSE_HOST) ---
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = ""
    langfuse_base_url: str = ""

    # --- Harness dataset name ---
    profu_langfuse_eval_dataset: str = "profu_clarify_step_by_step_eval"

    @field_validator("supabase_jwt_secret", mode="before")
    @classmethod
    def strip_supabase_jwt_secret(cls, value: Any) -> Any:
        """Normalize JWT secret whitespace."""
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator(
        "langfuse_public_key",
        "langfuse_secret_key",
        "langfuse_host",
        "langfuse_base_url",
        mode="before",
    )
    @classmethod
    def strip_quoted_langfuse_strings(cls, value: Any) -> Any:
        """Strip quotes from Langfuse vars (common .env copy-paste mistake)."""
        if isinstance(value, str):
            return _strip_quotes(value)
        return value

    @model_validator(mode="after")
    def resolve_langfuse_host(self) -> ProfuTestingSettings:
        """
        Effective Langfuse API host: LANGFUSE_HOST > LANGFUSE_BASE_URL > cloud default.

        Returns:
            Self with ``langfuse_host`` set for SDK construction.
        """
        if self.langfuse_host:
            self.langfuse_host = self.langfuse_host.rstrip("/")
        elif self.langfuse_base_url:
            self.langfuse_host = self.langfuse_base_url.rstrip("/")
        else:
            self.langfuse_host = "https://cloud.langfuse.com"
        return self

    @model_validator(mode="after")
    def normalize_eval_jwt(self) -> ProfuTestingSettings:
        """
        Strip accidental ``Bearer `` prefix from eval JWT.

        Returns:
            Self with normalized ``eval_jwt``.
        """
        token = self.eval_jwt.strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        self.eval_jwt = token
        return self

    @property
    def checklist_gemini_model(self) -> str:
        """
        Model name for checklist LLM: testing override or shared GEMINI_MODEL.

        Returns:
            Non-empty Gemini model id.
        """
        override = self.testing_gemini_model.strip()
        if override:
            return override
        return self.gemini_model.strip() or "gemini-2.0-flash"

    @property
    def resolved_api_base_url(self) -> str:
        """
        Base URL for clarify HTTP calls, without trailing slash.

        Returns:
            TESTING_API_BASE_URL, else API_BASE_URL, else localhost default.
        """
        for candidate in (self.testing_api_base_url, self.api_base_url):
            u = candidate.strip().rstrip("/")
            if u:
                return u
        return "http://127.0.0.1:8080"


@lru_cache(maxsize=1)
def get_testing_settings() -> ProfuTestingSettings:
    """
    Cached settings instance (reads env / .env once per process).

    Returns:
        Singleton ``ProfuTestingSettings``.
    """
    return ProfuTestingSettings()
