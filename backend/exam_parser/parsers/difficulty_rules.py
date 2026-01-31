"""
Difficulty classification for Romanian bacalaureat math problems (mate).
Uses explicit criteria to assign low / medium / high via an AI step.
"""
import os
from pathlib import Path


# Criteria for each level (Romanian bacalaureat mate: Subiectul I, II, III)
DIFFICULTY_CRITERIA = """
LOW difficulty:
- Single concept, direct application of one formula or definition.
- Short statement (one sentence, one equation or one "să se calculeze" / "să se arate că").
- Routine operations only: basic algebra, simple equations (linear, quadratic), basic trig (sin/cos/tan values), simple combinatorics (one C_n^k or sum), coordinates or area.
- No proof structure, no multi-step reasoning.
- Typical: Subiectul I items 1–4 style; "să se calculeze", "să se arate că" with a single identity or short computation.

MEDIUM difficulty:
- Two concepts combined or one non-trivial concept.
- Statement or items require 2–3 steps, or one short proof (e.g. "arate că" with a brief argument).
- Topics: inequalities, equations with parameters, remainder theorem, 2×2 matrices (operations, powers), sequences, basic limits of sequences, polynomial division.
- May have 2–3 sub-items (Subiectul II/III) with mixed types (compute + show).
- Typical: Subiectul I items 5–6; Subiectul II/III first sub-items (a, b).

HIGH difficulty:
- Multi-step proof, existence/uniqueness, or non-routine problem.
- Long or abstract statement; uses "să se demonstreze", "pentru orice", irreducibility, structure theorems.
- Topics: polynomial irreducibility, harder analysis (continuity, derivatives, integrals), geometry (loci, proofs), optimization, recurrence.
- Subiectul III style or harder Subiectul II: integration, limits of functions, "demonstreze că ... nu poate fi descompus".
- Typical: Subiectul II/III last sub-items (c, d); proofs that require several ideas.
"""

DIFFICULTY_CLASSIFY_PROMPT_TEMPLATE = """You classify the difficulty of a Romanian bacalaureat math (mate) problem.

Apply these criteria strictly:

""" + DIFFICULTY_CRITERIA + """

Problem to classify:
- statement: <<STATEMENT>>
- items (if any): <<ITEMS>>
- topic: <<TOPIC>>

Reply with exactly one word: low, medium, or high. No explanation."""


def classify_problem_difficulty(problem: dict) -> str:
    """
    Classify a single problem into low / medium / high using the criteria above.
    problem must have "statement", and optionally "items" (list of strings), "topic".
    """
    from google import genai

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")

    statement = (problem.get("statement") or "").strip()
    items = problem.get("items") or problem.get("choices") or []
    items_text = "\n".join(f"- {item}" for item in items) if items else "(none)"
    topic = (problem.get("topic") or "").strip() or "(unspecified)"

    prompt = (
        DIFFICULTY_CLASSIFY_PROMPT_TEMPLATE.replace("<<STATEMENT>>", statement[:2000])
        .replace("<<ITEMS>>", items_text[:1500])
        .replace("<<TOPIC>>", topic)
    )
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt],
    )
    raw = (response.text or "").strip().lower()
    if raw in ("low", "medium", "high"):
        return raw
    # Fallback: take first word if model added explanation
    for level in ("high", "medium", "low"):
        if level in raw:
            return level
    return "medium"


def reclassify_structured_data(data: dict) -> dict:
    """
    Update difficulty for every problem in structured output (s1, s2, or s3).
    Modifies data in place and returns it.
    """
    for key in ("s1", "s2", "s3"):
        if key not in data or not isinstance(data[key], list):
            continue
        for problem in data[key]:
            if isinstance(problem, dict) and "statement" in problem:
                problem["difficulty"] = classify_problem_difficulty(problem)
    return data
