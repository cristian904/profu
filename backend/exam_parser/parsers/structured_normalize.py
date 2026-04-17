"""
Normalization helpers for exam markdown → structured JSON (problems and solutions).
"""
from __future__ import annotations

import re
from typing import Any


def detect_subject(md_text: str) -> str | None:
    """
    Return ``s1``, ``s2``, or ``s3`` from exam-style headers in markdown.

    Barem/solution PDFs often omit parentheses; Roman numerals must be matched
    so ``II`` does not satisfy the ``I`` pattern (word boundaries).
    """
    if not (md_text or "").strip():
        return None
    text_lower = md_text.lower()
    # Check III / II before I so shorter numerals do not steal longer ones.
    if re.search(r"subiectul\s+iii\b", text_lower) or re.search(r"subiect\s+iii\b", text_lower):
        return "s3"
    if re.search(r"subiectul\s+ii\b", text_lower) or re.search(r"subiect\s+ii\b", text_lower):
        return "s2"
    if (
        re.search(r"subiectul\s+i\s*\(", text_lower)
        or re.search(r"subiectul\s+i\b", text_lower)
        or re.search(r"subiect\s+i\s*\(", text_lower)
        or re.search(r"subiect\s+i\b", text_lower)
    ):
        return "s1"
    return None


# Crawler-style stems: ``2009_M1_v1_s1`` → subject I for merge alignment.
_STEM_SUBJECT_SUFFIX_RE = re.compile(r"_s([123])$", re.IGNORECASE)


def infer_subject_from_stem(stem: str) -> str | None:
    """
    Return ``s1``/``s2``/``s3`` when the file stem ends with ``_s1`` / ``_s2`` / ``_s3``.

    Args:
        stem: Filename stem (no extension), e.g. ``2009_M1_v1_s1``.
    """
    if not stem:
        return None
    m = _STEM_SUBJECT_SUFFIX_RE.search(stem.strip())
    if not m:
        return None
    return f"s{m.group(1).lower()}"


def validate_and_normalize_problems(data: dict, expected_key: str | None) -> dict:
    """Keep list-valued s1/s2/s3 keys; optionally keep only expected_key."""
    keys = [k for k in ("s1", "s2", "s3") if k in data and isinstance(data.get(k), list)]
    if not keys:
        raise ValueError("Output must contain at least one of: s1, s2, s3 (array)")
    if expected_key and expected_key in keys:
        return {expected_key: data[expected_key]}
    return {k: data[k] for k in keys}


def normalize_solutions_output(data: dict) -> dict[str, Any]:
    """Keep only s1/s2/s3 keys that are lists; return dict with 0–3 keys."""
    out: dict[str, Any] = {}
    for key in ("s1", "s2", "s3"):
        if key in data and isinstance(data.get(key), list):
            out[key] = data[key]
    return out
