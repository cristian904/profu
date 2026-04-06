"""
Langfuse client singleton initialisation.

Call ``create_langfuse_client(settings)`` once at startup (e.g. in the
FastAPI lifespan) to initialise the OTel-backed Langfuse client.
Subsequent code can retrieve the same instance via ``get_langfuse_client()``.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional

from langfuse import Langfuse
from profu_logging.feature_logger import get_feature_logger

if TYPE_CHECKING:
    from ai_backend.config import Settings

LOG = get_feature_logger(source="langfuse")

# Module-level singleton — set by create_langfuse_client().
_client: Optional[Langfuse] = None


def create_langfuse_client(settings: "Settings") -> Langfuse:
    """
    Initialise and store the global Langfuse client.

    The underlying ``Langfuse`` class already maintains a per-public-key
    singleton via its ``LangfuseResourceManager``, so calling this more
    than once with the same keys is safe.

    Args:
        settings: Application settings containing Langfuse keys.

    Returns:
        The initialised ``Langfuse`` client instance.
    """
    global _client

    if os.environ.get("OTEL_SDK_DISABLED", "").lower() == "true":
        LOG.warning(
            "OTEL_SDK_DISABLED=true in the API process environment — OpenTelemetry export is off, "
            "so Langfuse will not show LangGraph traces. Unset it for local dev if you need tracing.",
            user_id=None,
        )

    host = settings.langfuse_host
    cwd = os.getcwd()
    keys_ok = bool(settings.langfuse_public_key and settings.langfuse_secret_key)

    if not keys_ok:
        LOG.warning(
            "Langfuse API keys missing in Settings — span export disabled. "
            "Pytest integration tests read repo-root .env; the live API only sees variables loaded "
            "into this process (run uvicorn from repo root so .env is found, or export LANGFUSE_*). "
            "Flutter flutter_app/.env does not configure the backend. "
            "Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in repo-root .env.",
            user_id=None,
        )
        # Match SDK pattern: fake credentials + tracing off avoids "no public_key" noise in logs.
        _client = Langfuse(
            tracing_enabled=False,
            public_key="fake",
            secret_key="fake",
        )
        # Always emit a grep-friendly INFO summary (some operators only scan for "Langfuse export").
        LOG.info(
            f"Langfuse export: disabled (no_credentials). host={host} cwd={cwd}",
            user_id=None,
        )
        return _client

    _client = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
        # Flush spans every 1 second so they appear in Langfuse promptly
        # (the default is 5 seconds which feels like spans are "missing").
        flush_interval=1.0,
    )

    tracing_on = getattr(_client, "_tracing_enabled", True)
    if not tracing_on:
        LOG.warning(
            "Langfuse client exists but tracing is disabled (check LANGFUSE_TRACING_ENABLED=false). "
            "No observations will be sent.",
            user_id=None,
        )
        LOG.info(
            f"Langfuse export: disabled (tracing_flag_off). host={host} cwd={cwd}",
            user_id=None,
        )
    else:
        LOG.info(
            f"Langfuse export: enabled. host={host} cwd={cwd} "
            "(LangGraph/LangChain observations are sent to this project).",
            user_id=None,
        )
    return _client


def get_langfuse_client() -> Langfuse:
    """
    Return the previously initialised Langfuse client.

    Raises:
        RuntimeError: If ``create_langfuse_client`` has not been called yet.
    """
    if _client is None:
        raise RuntimeError(
            "Langfuse client not initialised. "
            "Call create_langfuse_client(settings) during app startup."
        )
    return _client
