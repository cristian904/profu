"""
Shared helpers to parse JSON from LLM responses (code fences, LaTeX backslashes).
"""
from __future__ import annotations

import json
import re


def parse_json_from_llm_response(response_text: str) -> dict:
    """
    Strip optional markdown code fences and parse JSON.

    Doubles backslashes that are not valid JSON escapes so LaTeX like ``\\mathbb``
    survives ``json.loads``.
    """
    text = (response_text or "").strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    text = re.sub(r'(?<!\\)\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r"\\\\", text)
    return json.loads(text)
