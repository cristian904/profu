"""
Shared JSON extraction helpers for LLM outputs (markdown fences, raw_decode).
"""

import json
import re
from typing import Any


def extract_json_from_text(text: str) -> dict[str, Any]:
    """
    Extract and parse a JSON object from a text response.

    Uses json.JSONDecoder.raw_decode from the first ``{`` so nested objects parse correctly.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("No JSON found in response")

    decoder = json.JSONDecoder()
    search_from = 0

    fence = re.search(r"```(?:json)?\s*", text, re.IGNORECASE)
    if fence:
        brace_after = text.find("{", fence.end())
        if brace_after != -1:
            search_from = brace_after
        else:
            search_from = text.find("{")
    else:
        search_from = text.find("{")

    if search_from == -1:
        raise ValueError("No JSON found in response")

    try:
        obj, _end = decoder.raw_decode(text, search_from)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from response: {e!s}") from e

    if not isinstance(obj, dict):
        raise ValueError("Parsed JSON is not an object")

    return obj
