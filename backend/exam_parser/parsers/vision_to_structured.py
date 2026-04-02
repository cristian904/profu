"""
Extract structured JSON (s1/s2/s3 problems) from Gemini vision output markdown.
"""
import json
import os
import re
from pathlib import Path


EXTRACT_STRUCTURED_PROMPT = """You are given markdown text from a Romanian bacalaureat exam (one subject only: Subiectul I, II, or III).

Extract the problems into a single JSON object with exactly ONE of these keys: "s1", "s2", or "s3", depending on which subject this document contains.

Rules:
- Subiectul I (s1): usually 6 problems. Each has only a statement (no sub-items). Use "choices": [] for each (no multiple choice in these).
- Subiectul II (s2) and Subiectul III (s3): 2 problems each. Each has a "statement" and "items" (array of 3-4 sub-items). For each item save only the problem ask: the actual question or task text. Do not include points (e.g. "5p") or item labels (e.g. "a)", "b)", "c)") in the item strings; strip those and output only the question content.
- For every problem set "subject" to "mate".
- Infer "difficulty" as one of: "low", "medium", "high" based on the problem content.
- Infer "topic" as a short string (e.g. "radicals", "matrices", "limits", "polynomials", "geometry").
- Set "number" to the exercise number in the original document (1-6 for s1, 1-2 for s2/s3).

Output valid JSON only. No markdown, no code fence, no preamble. Exactly one key: "s1", "s2", or "s3".

Schema for s1:
{"s1": [{"statement": "...", "choices": [], "difficulty": "low", "subject": "mate", "topic": "...", "number": 1}, ...]}

Schema for s2 or s3 (items = only the problem ask text, no points or a)/b)/c) labels):
{"s2": [{"statement": "...", "items": ["Să se demonstreze că ...", "Să se calculeze ..."], "difficulty": "medium", "subject": "mate", "topic": "...", "number": 1}, ...]}

Markdown to process:
"""


def _detect_subject(md_text: str) -> str | None:
    """Return 's1', 's2', 's3' if a SUBIECTUL I/II/III header is found, else None."""
    text_lower = md_text.lower()
    if re.search(r"subiectul\s+i\s*\(", text_lower) or "subiectul i (" in text_lower:
        return "s1"
    if re.search(r"subiectul\s+ii\s*\(", text_lower) or "subiectul ii (" in text_lower:
        return "s2"
    if re.search(r"subiectul\s+iii\s*\(", text_lower) or "subiectul iii (" in text_lower:
        return "s3"
    return None


def _parse_json_from_response(response_text: str) -> dict:
    """Strip optional markdown code fence and parse JSON. Escape LaTeX backslashes for JSON."""
    text = (response_text or "").strip()
    # Remove ```json ... ``` if present
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    # Gemini often returns LaTeX like \mathbb, \sqrt inside strings; JSON allows only \" \\ \/ \b \f \n \r \t \uXXXX.
    # Double any backslash that is not part of a valid JSON escape. Use (?<!\\) so we don't double an already-doubled \ (e.g. \\e -> stay \\e).
    text = re.sub(r'(?<!\\)\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r"\\\\", text)
    return json.loads(text)


def _validate_and_normalize(data: dict, expected_key: str | None) -> dict:
    """Ensure exactly one of s1/s2/s3 exists; optionally keep only expected_key. Return single-key dict."""
    keys = [k for k in ("s1", "s2", "s3") if k in data and isinstance(data.get(k), list)]
    if not keys:
        raise ValueError("JSON must contain exactly one of: s1, s2, s3 (array)")
    if len(keys) > 1 and expected_key:
        data = {expected_key: data[expected_key]}
    elif len(keys) > 1:
        data = {keys[0]: data[keys[0]]}
    else:
        data = {keys[0]: data[keys[0]]}
    return data


def extract_structured_problems(md_path: str | Path, model_name: str = "gemini-2.5-flash") -> dict:
    """
    Read a Gemini vision output markdown file and return a structured JSON dict
    with exactly one of s1, s2, or s3 (array of problems). Each problem has
    statement, subject "mate", and inferred difficulty and topic.
    """
    from google import genai

    path = Path(md_path)
    if not path.is_file():
        raise FileNotFoundError(f"Markdown file not found: {md_path}")
    if path.suffix.lower() != ".md":
        raise ValueError(f"Expected .md file, got: {path.suffix}")

    md_text = path.read_text(encoding="utf-8")
    if not md_text.strip():
        raise ValueError(f"Empty file: {md_path}")

    expected_key = _detect_subject(md_text)
    if not expected_key:
        raise ValueError(
            "No SUBIECTUL I, II, or III header found in the document. Cannot determine subject."
        )

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")

    client = genai.Client(api_key=api_key)
    full_prompt = EXTRACT_STRUCTURED_PROMPT + "\n---\n\n" + md_text
    response = client.models.generate_content(
        model=model_name,
        contents=[full_prompt],
    )
    raw = (response.text or "").strip()
    if not raw:
        raise ValueError("Gemini returned empty response")

    try:
        data = _parse_json_from_response(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini did not return valid JSON: {e}") from e

    return _validate_and_normalize(data, expected_key)
