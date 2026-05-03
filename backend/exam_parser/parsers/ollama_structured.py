"""
Structured extraction from markdown using a local Ollama chat model.

Outputs are validated as JSON and normalized to the same dict shapes
as the legacy pipeline.
"""
from __future__ import annotations

import json
import logging
import traceback
from typing import Any

import httpx

from exam_parser.parsers.json_response_utils import parse_json_from_llm_response
from exam_parser.parsers.structured_models import ProblemsDocument, SolutionsDocument
from exam_parser.parsers.structured_normalize import (
    infer_subject_from_stem,
    validate_and_normalize_problems,
    normalize_solutions_output,
)
from exam_parser.parsers.structured_prompts import (
    EXTRACT_STRUCTURED_PROBLEMS_PROMPT,
    EXTRACT_STRUCTURED_SOLUTIONS_PROMPT,
    format_structured_solutions_repair_user_message,
)

_LOG = logging.getLogger(__name__)


class StructuredJsonParseError(ValueError):
    """Raised when structured JSON parsing/validation fails, with raw response attached."""

    def __init__(self, message: str, raw_response: str) -> None:
        super().__init__(message)
        self.raw_response = raw_response


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
    source_stem: str | None = None,
) -> dict:
    """
    Parse problem markdown into subject-keyed structured dict.

    Args:
        md_text: Markdown from Nougat (or equivalent).
        base_url: Ollama server URL.
        model: Ollama model id.
        source_stem: Optional source stem (e.g. ``2009_M1_v1_s2``) used as subject hint.

    Returns:
        Dict with one or more of ``s1``, ``s2``, ``s3``.

    Raises:
        ValueError: If model output is invalid JSON or has invalid schema.
        RuntimeError: On Ollama failures.
    """
    if not (md_text or "").strip():
        raise ValueError("Markdown text is empty")

    stem_hint = infer_subject_from_stem(source_stem or "")
    hint_block = ""
    if stem_hint is not None:
        hint_block = (
            "\n\nSOURCE SUBJECT CONSTRAINT (from filename): "
            f"{stem_hint}\n"
            "You MUST use this exact subject key in output.\n"
            f"- Include only key `{stem_hint}` at top level.\n"
            "- Do not output other subject keys.\n"
        )

    full_prompt = EXTRACT_STRUCTURED_PROBLEMS_PROMPT + hint_block + "\n---\n\n" + md_text
    raw = ollama_chat_text(base_url, model, full_prompt, request_json_format=True)

    try:
        data = parse_json_from_llm_response(raw)
    except Exception as exc:
        raise StructuredJsonParseError(f"Model did not return valid JSON: {exc}", raw) from exc
    if not isinstance(data, dict):
        raise StructuredJsonParseError("Model output must be a JSON object", raw)

    try:
        normalized = validate_and_normalize_problems(data, expected_key=stem_hint)
        doc = ProblemsDocument.model_validate(normalized)
    except ValueError as exc:
        raise StructuredJsonParseError(f"Model JSON schema invalid for problems: {exc}", raw) from exc

    out = doc.to_exam_dict()
    if not out:
        raise StructuredJsonParseError(
            "Problems output must contain at least one of: s1, s2, s3 (non-empty lists)",
            raw,
        )
    return out


def _parse_solutions_ollama_raw_to_dict(raw: str, stem_hint: str | None) -> dict:
    """
    Parse model JSON text, apply filename subject filter, and validate with Pydantic.

    Args:
        raw: Raw assistant text (JSON).
        stem_hint: If set, only ``stem_hint`` may appear as a top-level list key.

    Returns:
        Normalized solutions dict (``s1``/``s2``/``s3`` subsets).

    Raises:
        StructuredJsonParseError: On invalid JSON or schema mismatch.
    """
    try:
        data = parse_json_from_llm_response(raw)
    except Exception as exc:
        raise StructuredJsonParseError(f"Model did not return valid JSON: {exc}", raw) from exc
    if not isinstance(data, dict):
        raise StructuredJsonParseError("Model output must be a JSON object", raw)

    if stem_hint is not None:
        key_val = data.get(stem_hint)
        if isinstance(key_val, list):
            data = {stem_hint: key_val}
        elif key_val is None:
            raise StructuredJsonParseError(
                f'Filename requires top-level key "{stem_hint}" with an array of exercises; '
                "key missing or null.",
                raw,
            )
        else:
            preview = str(key_val)[:400]
            raise StructuredJsonParseError(
                f'Filename requires top-level key "{stem_hint}" to be a JSON array of exercise objects; '
                f"got {type(key_val).__name__}. Preview: {preview!r}",
                raw,
            )

    try:
        doc = SolutionsDocument.model_validate(normalize_solutions_output(data))
    except ValueError as exc:
        raise StructuredJsonParseError(f"Model JSON schema invalid for solutions: {exc}", raw) from exc

    normalized = normalize_solutions_output(doc.to_solution_dict())
    if not normalized:
        raise StructuredJsonParseError(
            "Solutions output must contain at least one of: s1, s2, s3 (non-empty lists)",
            raw,
        )
    return normalized


def scoring_scale_md_to_structured_ollama(
    md_text: str,
    *,
    base_url: str,
    model: str,
    source_stem: str | None = None,
    solution_repair_attempts: int = 1,
) -> dict:
    """
    Parse scoring-scale markdown into ``s1``/``s2``/``s3`` solution dict (legacy schema).

    On validation failure, performs up to ``solution_repair_attempts`` follow-up calls with the
    validator error and the invalid output so the model can return schema-compliant JSON.

    Args:
        md_text: Markdown from Nougat.
        base_url: Ollama server URL.
        model: Ollama model id.
        source_stem: Optional PDF/file stem (e.g. ``2009_M1_v1_s1``) for ``_sN`` subject hint.
        solution_repair_attempts: Extra Ollama calls after the first failed validation (default 1).

    Returns:
        Dict with up to three keys ``s1``, ``s2``, ``s3``.

    Raises:
        ValueError: If markdown text is empty.
        RuntimeError: On Ollama HTTP failures.
        StructuredJsonParseError: If all attempts fail validation.
    """
    if not (md_text or "").strip():
        raise ValueError("Markdown text is empty")

    stem_hint = infer_subject_from_stem(source_stem or "")
    full_prompt = EXTRACT_STRUCTURED_SOLUTIONS_PROMPT + "\n---\n\n" + md_text
    if stem_hint is not None:
        full_prompt += (
            "\n\nSOURCE SUBJECT CONSTRAINT (from filename): "
            f"{stem_hint}\n"
            "You MUST use this exact subject key in output.\n"
            f"- Include only key `{stem_hint}` at top level.\n"
            "- Do not output other subject keys.\n"
        )

    last_exc: StructuredJsonParseError | None = None
    max_rounds = 1 + max(0, solution_repair_attempts)

    for round_idx in range(max_rounds):
        if round_idx == 0:
            user_content = full_prompt
        else:
            assert last_exc is not None
            user_content = format_structured_solutions_repair_user_message(
                validation_error=str(last_exc),
                previous_raw=last_exc.raw_response,
                markdown_source=md_text,
                stem_hint=stem_hint,
            )
            _LOG.warning(
                "Solutions JSON validation failed; sending repair prompt (round %s/%s): %s",
                round_idx + 1,
                max_rounds,
                str(last_exc)[:800],
            )

        raw = ollama_chat_text(base_url, model, user_content, request_json_format=True)

        try:
            return _parse_solutions_ollama_raw_to_dict(raw, stem_hint)
        except StructuredJsonParseError as exc:
            last_exc = exc
            if round_idx == max_rounds - 1:
                raise
            _LOG.info(
                "Solutions structured parse will retry after error: %s",
                str(exc)[:500],
            )

    assert last_exc is not None
    raise last_exc


def log_ollama_error(logger: Any, exc: BaseException) -> None:
    """Emit structured error + traceback to the feature logger when available."""
    try:
        logger.error(exc, traceback=traceback.format_exc())
    except Exception:
        pass
