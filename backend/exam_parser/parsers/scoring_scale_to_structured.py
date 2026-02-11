"""
Extract structured JSON (s1/s2/s3 solution steps and scores) from scoring-scale markdown.
"""
import json
import os
import re
from typing import Any


EXTRACT_STRUCTURED_SOLUTIONS_PROMPT = """You are given markdown text from a Romanian bacalaureat scoring scale (barem/rezolvare). The document may contain Subiectul I only, II only, III only, or all three.

Output a single JSON object with up to three keys: "s1", "s2", "s3". Include only the keys for subjects that appear in the document.

Rules:
- **s1** (Subiectul I): array of objects. Each has "number" (exercise number in the document, e.g. 1-6) and "solution_steps". Do NOT include an "item" field for s1.
- **s2** and **s3** (Subiectul II, III): array of objects. Each has "number" (exercise number), "item" ("a", "b", "c", or "d"), and "solution_steps".
- **solution_steps**:
  - If the solution is described in a TABLE (one row per step with scores): output an array of objects: [{"step": "description of step", "score": <number>}, ...]. In the document, scores are usually written with a "p" suffix (e.g. "0,5p", "1p", "2p") — extract the numeric value only for the "score" field (e.g. 0.5, 1, 2). Use a decimal point in JSON.
  - If the solution is NOT in a table (plain text block): output "solution_steps" as a single STRING containing the full block of text for that exercise/item.

Match each solution block to the correct subject, exercise number, and item (a/b/c/d) as in the document. When the source has one step followed by one score (e.g. step line then "3p") repeated, output one {"step": "...", "score": ...} per pair; do not merge multiple steps into one or leave "step" null.

Output valid JSON only. No markdown, no code fence, no preamble.

Example with table-style steps (s1):
{"s1": [{"number": "1", "solution_steps": [{"step": "step 1", "score": 0.5}, {"step": "step 2", "score": 1}]}]}

Example with plain-text solution (s2):
{"s2": [{"number": "1", "item": "a", "solution_steps": "Full paragraph of solution text here."}]}

Markdown to process:
"""


def _parse_json_from_response(response_text: str) -> dict:
    """Strip optional markdown code fence and parse JSON. Escape LaTeX backslashes for JSON."""
    text = (response_text or "").strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    text = re.sub(
        r'(?<!\\)\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r"\\\\", text
    )
    return json.loads(text)


def _normalize_output(data: dict) -> dict:
    """Keep only s1/s2/s3 keys that are lists; return dict with 0–3 keys."""
    out: dict[str, Any] = {}
    for key in ("s1", "s2", "s3"):
        if key in data and isinstance(data.get(key), list):
            out[key] = data[key]
    return out


def scoring_scale_md_to_structured(md_text: str) -> dict:
    """
    Convert scoring-scale markdown to structured JSON with s1/s2/s3.
    Each entry has number, optional item (s2/s3), and solution_steps (array of
    {step, score} or a single string).
    """
    from google import genai

    if not (md_text or "").strip():
        raise ValueError("Markdown text is empty")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")

    client = genai.Client(api_key=api_key)
    full_prompt = EXTRACT_STRUCTURED_SOLUTIONS_PROMPT + "\n---\n\n" + md_text
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[full_prompt],
    )
    raw = (response.text or "").strip()
    if not raw:
        raise ValueError("Gemini returned empty response")

    try:
        data = _parse_json_from_response(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini did not return valid JSON: {e}") from e

    normalized = _normalize_output(data)
    if not normalized:
        raise ValueError("JSON must contain at least one of: s1, s2, s3 (array)")

    return normalized
