#!/usr/bin/env python3
"""
Validate and repair LaTeX inside merged exam JSON files using Gemini 2.5 Pro + Flash.

Pro evaluates each batch and returns structured lists of syntax issues; Flash repairs
text using those issue lists. Reads *_merged.json from crawler structured_output_merged
trees, writes corrected copies to parallel structured_output_merged_fixed directories.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import copy
import json
import logging
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

from dotenv import load_dotenv

# Repo layout: backend/exam_parser/fix_merged_latex.py
_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SCRIPT_DIR.parent
_CRAWLER_BASE = _BACKEND_DIR / "crawler"
_REPO_ROOT = _BACKEND_DIR.parent

MODEL_FLASH = "gemini-2.5-flash"
MODEL_PRO = "gemini-2.5-pro"
DEFAULT_BATCH_SIZE = 20
LOG_TRUNCATE = 4000

PRO_EVAL_SYSTEM_EN = """You are an expert evaluator for educational text (often Romanian) that may contain Markdown and LaTeX math.

For EVERY field you must read the ENTIRE string from start to finish and inspect ALL math segments. Do not stop after the first problem.

Report only LaTeX delimiter and math-syntax problems, not spelling or Romanian grammar.

What counts as an issue (each distinct problem = one separate string in the "issues" array):
- Wrong or forbidden delimiters: only $...$ (inline) and $$...$$ (display) are allowed in the target app. \\(...\\), \\[...\\], or other math wrappers should be listed as issues.
- Unbalanced or stray $ / $$.
- Invalid or non-KaTeX LaTeX inside math segments (unbalanced braces, bad commands, illegal subscripts/superscripts, unknown package-only commands, etc.).

You MUST list EVERY distinct issue you find for that field. An empty "issues" array means the field is fully valid.

Respond with valid JSON only: no markdown fences, no text before or after."""

PRO_EVAL_USER_TEMPLATE_EN = """You receive a list of fields (id + full text). For each id, analyze the COMPLETE string.

Return EXACTLY one JSON array, one object per input field, IN THE SAME ORDER:
[{{"id":"<id>","issues":["<first problem>","<second problem>",...]}}, ...]

Rules:
- "issues" must contain every distinct syntax/delimiter/LaTeX problem for that field, as short clear English descriptions (one string per problem).
- If there are no problems, return "issues": [].
- Do not omit problems; scan the whole string.

Fields:
{payload}
"""

FLASH_REPAIR_SYSTEM_EN = """You repair one string that may contain Markdown and LaTeX math for a Flutter app.

You are given the original text plus a list of syntax problems found by another model. You MUST address every listed issue in the full string.

Mandatory rules:
- The app uses flutter_math_fork: ONLY $...$ (inline) and $$...$$ (display). Never use \\(...\\), \\[...\\], <latex>, or other delimiters for math.
- Math inside delimiters must be KaTeX-compatible LaTeX (standard bac / high-school level).
- Preserve meaning, language, and Markdown structure (lists, headings) as closely as possible; change only what is needed to fix the listed problems and any directly related breakage.
- Fix ALL listed issues in one response; do not leave any of them unaddressed.

Output a single string: the fully repaired text. No JSON wrapper, no ``` fences, no commentary."""

FLASH_REPAIR_USER_TEMPLATE_EN = """Identified syntax problems (fix every item below):
{issues_block}

Original text (complete):
---
{text}
---

Return only the repaired full string. If the list above is empty, return the original unchanged."""

T = TypeVar("T")

logger = logging.getLogger(__name__)
_LOG_LOCK = threading.Lock()


def _setup_logging() -> None:
    """Configure root logging for console progress."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
        stream=sys.stdout,
    )


def _load_env() -> None:
    """Load GOOGLE_API_KEY from repo root .env if present."""
    env_path = _REPO_ROOT / ".env"
    if env_path.is_file():
        load_dotenv(env_path)
        logger.info("Loaded environment from %s", env_path)
    else:
        load_dotenv()
        logger.warning(".env not found at %s; relying on process environment", env_path)


def _parse_json_from_model_text(raw: str) -> Any:
    """
    Strip optional markdown fence and parse JSON from a model response.
    Duplicates the exam_parser approach for LaTeX backslashes in JSON strings.
    """
    text = (raw or "").strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    text = re.sub(
        r'(?<!\\)\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})',
        r"\\\\",
        text,
    )
    return json.loads(text)


def _is_retriable_error(exc: BaseException) -> bool:
    """Return True if the API error is worth retrying (rate limit / transient)."""
    msg = str(exc).lower()
    if "429" in msg or "resource exhausted" in msg or "503" in msg or "502" in msg:
        return True
    if "timeout" in msg or "timed out" in msg:
        return True
    code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if code in (429, 500, 502, 503):
        return True
    return False


def _with_retries(
    operation: Callable[[], T],
    *,
    max_attempts: int = 5,
    base_delay_s: float = 1.5,
) -> T:
    """
    Run operation with exponential backoff on retriable failures.

    Args:
        operation: Zero-argument callable to run.
        max_attempts: Maximum attempts before re-raising.
        base_delay_s: Base seconds for backoff (multiplied by 2**attempt).

    Returns:
        The operation result.

    Raises:
        The last exception if all attempts fail.
    """
    last_exc: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return operation()
        except Exception as e:  # noqa: BLE001 — API surface varies
            last_exc = e
            logger.error(
                "Attempt %s/%s failed: %s",
                attempt + 1,
                max_attempts,
                e,
            )
            if attempt >= max_attempts - 1 or not _is_retriable_error(e):
                raise
            delay = base_delay_s * (2**attempt)
            logger.info("Retrying in %.1f s (retriable error)", delay)
            time.sleep(delay)
    raise RuntimeError("unreachable") from last_exc


def collect_latex_fields(data: dict[str, Any]) -> list[tuple[str, list[str | int], str]]:
    """
    Enumerate all string fields that may contain LaTeX.

    Args:
        data: Merged exam dict with optional s1, s2, s3 arrays.

    Returns:
        List of (field_id, path_segments, text). path_segments index into dicts/lists.
    """
    out: list[tuple[str, list[str | int], str]] = []
    for subj in ("s1", "s2", "s3"):
        if subj not in data or not isinstance(data[subj], list):
            continue
        problems: list[Any] = data[subj]
        for pi, prob in enumerate(problems):
            if not isinstance(prob, dict):
                continue
            st = prob.get("statement")
            if isinstance(st, str) and st.strip():
                fid = f"{subj}/{pi}/statement"
                out.append((fid, [subj, pi, "statement"], st))
            ch = prob.get("choices")
            if isinstance(ch, list):
                for ci, c in enumerate(ch):
                    if isinstance(c, str) and c.strip():
                        fid = f"{subj}/{pi}/choices/{ci}"
                        out.append((fid, [subj, pi, "choices", ci], c))
            items = prob.get("items")
            if isinstance(items, list):
                for ii, it in enumerate(items):
                    if isinstance(it, str) and it.strip():
                        fid = f"{subj}/{pi}/items/{ii}"
                        out.append((fid, [subj, pi, "items", ii], it))
            if subj == "s1":
                ss = prob.get("solution_steps")
                if isinstance(ss, str) and ss.strip():
                    fid = f"{subj}/{pi}/solution_steps"
                    out.append((fid, [subj, pi, "solution_steps"], ss))
                elif isinstance(ss, list):
                    for si, step_obj in enumerate(ss):
                        if not isinstance(step_obj, dict):
                            continue
                        step_txt = step_obj.get("step")
                        if isinstance(step_txt, str) and step_txt.strip():
                            fid = f"{subj}/{pi}/solution_steps/{si}/step"
                            out.append(
                                (fid, [subj, pi, "solution_steps", si, "step"], step_txt),
                            )
            else:
                item_sols = prob.get("item_solutions")
                if isinstance(item_sols, list):
                    for isi, item_sol in enumerate(item_sols):
                        if not isinstance(item_sol, dict):
                            continue
                        ss = item_sol.get("solution_steps")
                        if isinstance(ss, str) and ss.strip():
                            fid = f"{subj}/{pi}/item_solutions/{isi}/solution_steps"
                            out.append(
                                (
                                    fid,
                                    [subj, pi, "item_solutions", isi, "solution_steps"],
                                    ss,
                                ),
                            )
                        elif isinstance(ss, list):
                            for si, step_obj in enumerate(ss):
                                if not isinstance(step_obj, dict):
                                    continue
                                step_txt = step_obj.get("step")
                                if isinstance(step_txt, str) and step_txt.strip():
                                    fid = (
                                        f"{subj}/{pi}/item_solutions/{isi}/"
                                        f"solution_steps/{si}/step"
                                    )
                                    out.append(
                                        (
                                            fid,
                                            [
                                                subj,
                                                pi,
                                                "item_solutions",
                                                isi,
                                                "solution_steps",
                                                si,
                                                "step",
                                            ],
                                            step_txt,
                                        ),
                                    )
    return out


def get_at(root: dict[str, Any], path: list[str | int]) -> Any:
    """Navigate root using path segments (str keys or int indices)."""
    cur: Any = root
    for p in path:
        if isinstance(p, int):
            cur = cur[p]
        else:
            cur = cur[p]
    return cur


def set_at(root: dict[str, Any], path: list[str | int], value: str) -> None:
    """Set the value at path in root (mutates nested dicts/lists)."""
    cur: Any = root
    for p in path[:-1]:
        if isinstance(p, int):
            cur = cur[p]
        else:
            cur = cur[p]
    last = path[-1]
    if isinstance(last, int):
        cur[last] = value
    else:
        cur[last] = value


def _build_eval_payload(batch: list[tuple[str, str]]) -> str:
    """Format batch items as JSON lines for the Pro evaluation prompt."""
    lines: list[str] = []
    for fid, text in batch:
        lines.append(json.dumps({"id": fid, "text": text}, ensure_ascii=False))
    return "\n".join(lines)


def _normalize_issues_list(raw_issues: Any) -> list[str]:
    """Turn model output into a clean list of non-empty issue strings."""
    if raw_issues is None:
        return []
    if isinstance(raw_issues, str) and raw_issues.strip():
        return [raw_issues.strip()]
    if not isinstance(raw_issues, list):
        return []
    out: list[str] = []
    for x in raw_issues:
        if isinstance(x, str) and x.strip():
            out.append(x.strip())
    return out


def evaluate_batch_pro(
    client: Any,
    batch: list[tuple[str, str]],
    model_name: str = MODEL_PRO,
) -> dict[str, list[str]]:
    """
    Ask Gemini to evaluate a batch of fields and return syntax issue lists.

    Args:
        client: google.genai.Client instance.
        batch: List of (field_id, text).
        model_name: The Gemini model to use.

    Returns:
        Mapping field_id -> list of issue descriptions (empty if valid).
    """
    from google.genai import types

    if not batch:
        return {}

    payload = _build_eval_payload(batch)
    user_msg = PRO_EVAL_USER_TEMPLATE_EN.format(payload=payload)

    def _call() -> Any:
        return client.models.generate_content(
            model=model_name,
            contents=[user_msg],
            config=types.GenerateContentConfig(
                temperature=0.0,
                system_instruction=PRO_EVAL_SYSTEM_EN,
            ),
        )

    response = _with_retries(_call)
    raw = (response.text or "").strip()
    if not raw:
        logger.error("Pro returned empty evaluation response")
        raise ValueError("empty Pro evaluation response")

    parsed: Any
    try:
        parsed = _parse_json_from_model_text(raw)
    except json.JSONDecodeError as first_err:
        logger.warning("Pro evaluation JSON parse failed (%s); retrying once", first_err)
        retry_msg = (
            user_msg
            + "\n\nERROR: Your previous reply was not valid JSON. "
            "Return ONLY the JSON array, no other text."
        )

        def _call_retry() -> Any:
            return client.models.generate_content(
                model=MODEL_PRO,
                contents=[retry_msg],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    system_instruction=PRO_EVAL_SYSTEM_EN,
                ),
            )

        response2 = _with_retries(_call_retry)
        raw2 = (response2.text or "").strip()
        try:
            parsed = _parse_json_from_model_text(raw2)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse Pro evaluation JSON after retry: %s", e)
            raise

    if not isinstance(parsed, list):
        raise ValueError(f"Expected JSON array from Pro, got {type(parsed)}")

    result: dict[str, list[str]] = {}
    for item in parsed:
        if not isinstance(item, dict):
            continue
        fid = item.get("id")
        if not isinstance(fid, str):
            continue
        issues = _normalize_issues_list(item.get("issues"))
        if not issues:
            legacy = item.get("reason")
            if isinstance(legacy, str) and legacy.strip():
                issues = [legacy.strip()]
        result[fid] = issues

    for fid, _ in batch:
        if fid not in result:
            logger.warning("Pro omitted id %s; assuming unknown issues", fid)
            result[fid] = ["Missing from evaluator response"]
    return result


def _format_issues_block(issues: list[str]) -> str:
    """Format issue strings for the Flash repair user prompt."""
    if not issues:
        return "(none)"
    return "\n".join(f"{i + 1}. {issue}" for i, issue in enumerate(issues))


def _strip_markdown_fence(text: str) -> str:
    """Remove a single outer ``` fence if the model wrapped the answer."""
    fixed = text.strip()
    if fixed.startswith("```"):
        lines = fixed.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        fixed = "\n".join(lines).strip()
    return fixed


def repair_with_flash(
    client: Any,
    text: str,
    issues: list[str],
    model_name: str = MODEL_FLASH,
) -> str:
    """
    Ask Gemini to repair LaTeX using Pro's issue list (retry if empty/unchanged).

    Args:
        client: google.genai.Client instance.
        text: Original field text.
        issues: Syntax problems from evaluator (non-empty before calling).
        model_name: Model to use for the payload.

    Returns:
        Repaired text.

    Raises:
        ValueError: If model cannot produce a changed non-empty string after retry.
    """
    from google.genai import types

    issues_block = _format_issues_block(issues)
    strict_extra = ""
    for attempt in range(2):
        user_msg = FLASH_REPAIR_USER_TEMPLATE_EN.format(
            issues_block=issues_block,
            text=text,
        )
        if strict_extra:
            user_msg = user_msg + strict_extra

        def _call() -> Any:
            return client.models.generate_content(
                model=model_name,
                contents=[user_msg],
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    system_instruction=FLASH_REPAIR_SYSTEM_EN,
                ),
            )

        response = _with_retries(_call)
        fixed = _strip_markdown_fence(response.text or "")
        if fixed and fixed != text:
            return fixed
        logger.warning(
            "Flash repair attempt %s produced empty or identical output; retrying=%s",
            attempt + 1,
            attempt == 0,
        )
        strict_extra = (
            "\n\nIMPORTANT: Your previous answer was empty or identical. "
            "Apply ALL fixes required by the numbered issue list above; output the "
            "full corrected string with every $...$ and $$...$$ block valid."
        )

    raise ValueError("Flash returned empty or unchanged text after retry")


def append_fix_log(
    log_path: Path,
    entry: dict[str, Any],
) -> None:
    """Append one JSON line to the fix log (creates parent dirs)."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with _LOG_LOCK:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _truncate_for_log(s: str) -> str:
    """Truncate long strings for log lines."""
    if len(s) <= LOG_TRUNCATE:
        return s
    return s[:LOG_TRUNCATE] + f"... [truncated, len={len(s)}]"


