"""
Structured extraction from markdown using a local Ollama chat model.

Outputs are validated as Markdown + fenced YAML (LaTeX-safe), then normalized
to the same dict shapes as the legacy JSON pipeline.
"""
from __future__ import annotations

import json
import traceback
from typing import Any

import httpx

from exam_parser.parsers.structured_markdown import (
    normalize_llm_markdown_response,
    parse_problems_markdown,
    parse_solutions_markdown,
)
from exam_parser.parsers.structured_normalize import (
    detect_subject,
    infer_subject_from_stem,
    normalize_solutions_output,
)
from exam_parser.parsers.structured_prompts import (
    EXTRACT_STRUCTURED_PROBLEMS_PROMPT,
    EXTRACT_STRUCTURED_SOLUTIONS_PROMPT,
)


def ollama_chat_text(
    base_url: str,
    model: str,
    user_content: str,
    *,
    timeout_sec: float = 900.0,
    request_json_format: bool = False,
) -> str:
    """
    Call Ollama ``/api/chat`` and return the assistant message content (non-streaming).

    Args:
        base_url: Ollama base URL (e.g. ``http://127.0.0.1:11434``).
        model: Ollama model name.
        user_content: Full user message (prompt + document).
        timeout_sec: HTTP timeout for large documents.
        request_json_format: When True, set ``format: "json"`` (legacy JSON-only mode).

    Returns:
        Raw assistant text.

    Raises:
        RuntimeError: On HTTP errors or empty model response.
    """
    url = f"{base_url.rstrip('/')}/api/chat"
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": user_content}],
        "stream": False,
    }
    if request_json_format:
        payload["format"] = "json"

    try:
        with httpx.Client(timeout=timeout_sec) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Ollama HTTP error: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Ollama returned non-JSON body: {exc}") from exc

    msg = body.get("message") or {}
    content = (msg.get("content") or "").strip()
    if not content:
        raise RuntimeError("Ollama returned empty message content")
    return content


def extract_structured_problems_from_markdown(
    md_text: str,
    *,
    base_url: str,
    model: str,
) -> dict:
    """
    Parse problem markdown into subject-keyed structured dict.

    Args:
        md_text: Markdown from Nougat (or equivalent).
        base_url: Ollama server URL.
        model: Ollama model id.

    Returns:
        Dict with one or more of ``s1``, ``s2``, ``s3``.

    Raises:
        ValueError: If subject headers are missing or structured markdown is invalid.
        RuntimeError: On Ollama failures.
    """
    if not (md_text or "").strip():
        raise ValueError("Markdown text is empty")

    inferred_key = detect_subject(md_text)
    if not inferred_key:
        raise ValueError(
            "No Subiect I/II/III header found in source markdown; cannot infer problems subject."
        )

    full_prompt = EXTRACT_STRUCTURED_PROBLEMS_PROMPT + "\n---\n\n" + md_text
    raw = ollama_chat_text(base_url, model, full_prompt, request_json_format=False)
    raw = normalize_llm_markdown_response(raw)

    try:
        doc = parse_problems_markdown(raw, inferred_subject=inferred_key)
    except ValueError as exc:
        raise ValueError(f"Model did not return valid structured markdown: {exc}") from exc

    data = doc.to_exam_dict()
    if not data:
        raise ValueError("Problems output must contain at least one of: s1, s2, s3 (non-empty lists)")
    return data


def scoring_scale_md_to_structured_ollama(
    md_text: str,
    *,
    base_url: str,
    model: str,
    source_stem: str | None = None,
) -> dict:
    """
    Parse scoring-scale markdown into ``s1``/``s2``/``s3`` solution dict (legacy schema).

    Args:
        md_text: Markdown from Nougat.
        base_url: Ollama server URL.
        model: Ollama model id.
        source_stem: Optional PDF/file stem (e.g. ``2009_M1_v1_s1``) for ``_sN`` subject hint.

    Returns:
        Dict with up to three keys ``s1``, ``s2``, ``s3``.

    Raises:
        ValueError: If structured markdown is invalid or empty subject lists.
        RuntimeError: On Ollama failures.
    """
    if not (md_text or "").strip():
        raise ValueError("Markdown text is empty")

    full_prompt = EXTRACT_STRUCTURED_SOLUTIONS_PROMPT + "\n---\n\n" + md_text
    raw = ollama_chat_text(base_url, model, full_prompt, request_json_format=False)
    raw = normalize_llm_markdown_response(raw)

    inferred_subject = detect_subject(md_text) or infer_subject_from_stem(source_stem or "")

    try:
        doc = parse_solutions_markdown(raw, inferred_subject=inferred_subject)
    except ValueError as exc:
        raise ValueError(f"Model did not return valid structured markdown: {exc}") from exc

    data = doc.to_solution_dict()
    normalized = normalize_solutions_output(data)
    if not normalized:
        raise ValueError("Solutions output must contain at least one of: s1, s2, s3 (non-empty lists)")
    return normalized


def log_ollama_error(logger: Any, exc: BaseException) -> None:
    """Emit structured error + traceback to the feature logger when available."""
    try:
        logger.error(exc, traceback=traceback.format_exc())
    except Exception:
        pass
