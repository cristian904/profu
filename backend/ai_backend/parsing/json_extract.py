"""
Shared JSON extraction helpers.

Used to parse LLM responses that may include JSON wrapped in Markdown code fences.
"""

import json
import re
from typing import Any


def extract_json_from_text(text: str) -> dict[str, Any]:
    """
    Extract and parse a JSON object from a text response.

    The response may contain:
    - a Markdown fenced block ```json { ... } ```
    - or a raw JSON object in the text.

    Args:
        text: LLM output text that should contain a JSON object.

    Returns:
        Parsed JSON dictionary.

    Raises:
        ValueError: When no JSON object can be found or parsing fails.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("No JSON found in response")

    try:
        # Try to find JSON in code blocks first
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced:
            return json.loads(fenced.group(1))

        # Try to find raw JSON object
        raw = re.search(r"\{.*\}", text, re.DOTALL)
        if raw:
            return json.loads(raw.group(0))
    except Exception as e:
        raise ValueError(f"Failed to parse JSON from response: {e!s}") from e

    raise ValueError("No JSON found in response")

