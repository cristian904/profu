#!/usr/bin/env python3
"""
Seed Langfuse Prompt Management with all ``system_prompt`` entries from ``ai_backend/prompts.yaml``.

Loads the repository ``.env`` from the project root (same pattern as ``ai_backend``) so
``LANGFUSE_PUBLIC_KEY``, ``LANGFUSE_SECRET_KEY``, and optional ``LANGFUSE_HOST`` (or
``LANGFUSE_BASE_URL``) are available. For local Langfuse use
``LANGFUSE_HOST=http://localhost:3000`` (or the same value in ``LANGFUSE_BASE_URL``).

There is **no separate project name** in this script: Langfuse ties API keys to a single project,
so prompts are created in whatever project those keys belong to (choose keys from the target
project in the Langfuse UI).

Usage (from repository root)::

    uv run python scripts/seed_langfuse_prompts.py
    uv run python scripts/seed_langfuse_prompts.py --dry-run
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Iterator

import yaml
from dotenv import load_dotenv
from langfuse import Langfuse
from profu_logging.feature_logger import get_feature_logger

LOG = get_feature_logger(source="seed_langfuse_prompts")

# Prefix for Langfuse prompt names (folder-like namespace)
PROMPT_NAME_PREFIX = "profu"

# Default path to prompts.yaml relative to repository root
DEFAULT_PROMPTS_REL = Path("backend") / "ai_backend" / "prompts.yaml"


def _repo_root() -> Path:
    """Resolve repository root from this file location (``scripts/``)."""
    return Path(__file__).resolve().parent.parent


def _load_dotenv(repo_root: Path, env_file: Path | None) -> None:
    """
    Load environment variables from a ``.env`` file before reading Langfuse credentials.

    Uses ``override=True`` so values from the chosen file replace any ``LANGFUSE_*`` (and
    other keys) already present in the process environment. Stale shell exports are a common
    cause of 401 errors (e.g. wrong ``LANGFUSE_HOST`` left over from another session).

    Args:
        repo_root: Repository root directory.
        env_file: Explicit path to env file, or ``None`` to use ``repo_root / .env``.
    """
    path = env_file if env_file is not None else repo_root / ".env"
    if not path.is_file():
        LOG.info(f"No env file at {path}; using process environment only", user_id=None)
        return
    load_dotenv(path, override=True)
    LOG.info(f"Loaded environment from {path} (overrides existing process env for same keys)", user_id=None)


def _load_prompts_yaml(path: Path) -> dict[str, Any]:
    """
    Load and parse ``prompts.yaml``.

    Args:
        path: Absolute path to ``prompts.yaml``.

    Returns:
        Parsed YAML as a dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If YAML is invalid.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Prompts file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("prompts.yaml root must be a mapping")
    return data


def iter_system_prompts(node: Any, path_parts: tuple[str, ...] = ()) -> Iterator[tuple[str, str]]:
    """
    Yield ``(relative_path, text)`` for every ``system_prompt`` string in the tree.

    Example paths: ``clarify_chat``, ``guided_learning/prerequisite_generator``.

    Args:
        node: Current YAML subtree (dict, list, or scalar).
        path_parts: Keys from root to parent of ``system_prompt``.

    Yields:
        Tuples of slash-separated path and prompt text.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "system_prompt" and isinstance(value, str):
                rel = "/".join(path_parts) if path_parts else "system_prompt"
                yield rel, value.strip()
            elif isinstance(value, (dict, list)):
                yield from iter_system_prompts(value, path_parts + (key,))
    elif isinstance(node, list):
        for item in node:
            yield from iter_system_prompts(item, path_parts)


def _strip_env_quotes(value: str) -> str:
    """
    Remove one pair of surrounding quotes from a string (common in ``.env`` files).

    Args:
        value: Raw environment value.

    Returns:
        Stripped string without outer quotes when present.
    """
    s = value.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1].strip()
    return s


def _validate_langfuse_api_keys(public_key: str, secret_key: str) -> None:
    """
    Reject obvious placeholder values that cause 401 (unreplaced README examples).

    Self-hosted Langfuse does **not** put ``pk-lf`` / ``sk-lf`` keys in ``.langfuse/.env``;
    they are created in the web UI per project.

    Args:
        public_key: ``LANGFUSE_PUBLIC_KEY`` after stripping quotes.
        secret_key: ``LANGFUSE_SECRET_KEY`` after stripping quotes.

    Raises:
        SystemExit: If keys look invalid or unreplaced.
    """
    for label, value in (
        ("LANGFUSE_PUBLIC_KEY", public_key),
        ("LANGFUSE_SECRET_KEY", secret_key),
    ):
        if "..." in value:
            LOG.error(
                f"{label} still contains '...' — that is a documentation placeholder, not a real key. "
                "Start Langfuse locally, open http://localhost:3000 (or your LANGFUSE_PORT), sign in, "
                "then Project settings → API keys and paste the full pk-lf- and sk-lf- values into the "
                "repository root .env (see scripts/README.md).",
                user_id=None,
                traceback=None,
            )
            raise SystemExit(1)
        if len(value) < 25:
            LOG.error(
                f"{label} is too short ({len(value)} chars). Use the full key from Langfuse project settings.",
                user_id=None,
                traceback=None,
            )
            raise SystemExit(1)


def _resolve_langfuse_host() -> str:
    """
    Match ``ai_backend.config.Settings``: prefer ``LANGFUSE_HOST``, then ``LANGFUSE_BASE_URL``.

    Returns:
        Base URL without trailing slash (default: Langfuse Cloud).
    """
    h = _strip_env_quotes(os.environ.get("LANGFUSE_HOST", ""))
    b = _strip_env_quotes(os.environ.get("LANGFUSE_BASE_URL", ""))
    if h:
        return h.rstrip("/")
    if b:
        return b.rstrip("/")
    return "https://cloud.langfuse.com"


def _langfuse_prompt_name(relative_path: str) -> str:
    """
    Build the Langfuse prompt name from a YAML path segment.

    Args:
        relative_path: Path like ``clarify_chat`` or ``guided_learning/prerequisite_generator``.

    Returns:
        Namespaced name, e.g. ``profu/clarify_chat``.
    """
    return f"{PROMPT_NAME_PREFIX}/{relative_path}"


def _create_langfuse_client() -> Langfuse:
    """
    Build a Langfuse client from environment variables.

    Returns:
        Configured ``Langfuse`` instance.

    Raises:
        SystemExit: If required keys are missing or credentials fail ``auth_check``.
    """
    public_key = _strip_env_quotes(os.environ.get("LANGFUSE_PUBLIC_KEY", ""))
    secret_key = _strip_env_quotes(os.environ.get("LANGFUSE_SECRET_KEY", ""))
    host = _resolve_langfuse_host()
    if not public_key or not secret_key:
        LOG.error(
            "Missing LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY. "
            "Set them in the environment or in .env at the repository root.",
            user_id=None,
            traceback=None,
        )
        raise SystemExit(1)
    _validate_langfuse_api_keys(public_key, secret_key)
    pk_hint = f"{public_key[:16]}..." if len(public_key) > 16 else public_key
    LOG.info(
        f"Connecting to Langfuse host={host}, public_key_prefix={pk_hint}",
        user_id=None,
    )
    client = Langfuse(public_key=public_key, secret_key=secret_key, base_url=host)
    try:
        client.auth_check()
    except Exception as e:
        LOG.error(
            f"Langfuse authentication failed: {e!s}. "
            "Use API keys from the same deployment as LANGFUSE_HOST "
            "(e.g. local UI at http://localhost:3000 → keys from Settings; "
            "cloud keys require LANGFUSE_HOST=https://cloud.langfuse.com). "
            "Check LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, and LANGFUSE_HOST or LANGFUSE_BASE_URL.",
            user_id=None,
            traceback=None,
        )
        raise SystemExit(1) from e
    return client


def main() -> None:
    """CLI entry: parse args, load YAML, create or dry-run prompts in Langfuse."""
    parser = argparse.ArgumentParser(
        description="Seed Langfuse prompts from ai_backend/prompts.yaml",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print prompt names and sizes without calling Langfuse",
    )
    parser.add_argument(
        "--prompts-file",
        type=Path,
        default=None,
        help=f"Override path to prompts.yaml (default: {DEFAULT_PROMPTS_REL})",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Path to .env (default: <repo>/.env). Ignored if file does not exist.",
    )
    args = parser.parse_args()

    root = _repo_root()
    _load_dotenv(root, args.env_file)
    prompts_path = args.prompts_file
    if prompts_path is None:
        prompts_path = root / DEFAULT_PROMPTS_REL
    else:
        prompts_path = prompts_path.resolve()

    try:
        data = _load_prompts_yaml(prompts_path)
    except Exception as e:
        LOG.error(str(e), user_id=None, traceback=None)
        raise SystemExit(1) from e

    items = list(iter_system_prompts(data))
    if not items:
        LOG.warning("No system_prompt entries found in YAML", user_id=None)
        raise SystemExit(0)

    LOG.info(f"Found {len(items)} system_prompt(s) in {prompts_path}", user_id=None)

    if args.dry_run:
        for rel, text in sorted(items, key=lambda x: x[0]):
            name = _langfuse_prompt_name(rel)
            print(f"{name}\tchars={len(text)}")
        LOG.info("Dry run finished; no API calls made", user_id=None)
        return

    try:
        client = _create_langfuse_client()
    except SystemExit:
        raise

    created = 0
    failed = 0
    for rel, text in sorted(items, key=lambda x: x[0]):
        name = _langfuse_prompt_name(rel)
        try:
            client.create_prompt(
                name=name,
                prompt=text,
                type="text",
                labels=["production"],
                tags=["ai_backend", "seeded", "prompts.yaml"],
                commit_message=f"Seed from prompts.yaml ({rel})",
            )
            LOG.info(f"Created prompt: {name} (len={len(text)})", user_id=None)
            created += 1
        except Exception as e:
            failed += 1
            LOG.error(
                f"Failed to create prompt {name}: {e!s}",
                user_id=None,
                traceback=None,
            )

    LOG.info(
        f"Done. created={created}, failed={failed}, total={len(items)}",
        user_id=None,
    )
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
