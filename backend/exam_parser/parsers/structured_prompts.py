"""
Prompts for JSON structured extraction (exam text may be Romanian; instructions in English).
"""
from __future__ import annotations

EXTRACT_STRUCTURED_PROBLEMS_PROMPT = """You receive markdown with Romanian math exam problems. The document may contain only s1, only s2, only s3, or multiple subjects.

Return **ONLY** JSON (no markdown, no explanations), with this top-level shape:
{
  "s1": [ ... ],
  "s2": [ ... ],
  "s3": [ ... ]
}

Each problem object must use this schema:
- s1 problem:
  {"number": 1, "statement": "..."}
- s2/s3 problem:
  {"number": 1, "statement": "...", "items": ["a) ...", "b) ...", "c) ..."]}

MANDATORY RULES:
1) **EXACT COPY, character-by-character** for `statement` and `items`.
2) Do not rephrase, correct, or translate.
3) `items` appears only when the source subject/problem has sub-items (S2/S3: always 3 items).
4) Do not output `choices` field.
5) For each subject present in source, include its section (`s1`/`s2`/`s3`).
6) If source does not explicitly contain "Subiect I/II/III", infer the correct subject from content and keep it
   consistent in top-level JSON keys.
7) **Fixed Baccalaureate shape (mandatory whenever that subject key is present):**
   - `s1` array length must be **exactly 6** (six separate exercise objects, `number` 1…6).
   - `s2` array length must be **exactly 2**; each exercise has **exactly 3** `items` strings (sub-points **a**, **b**, **c**).
   - `s3` array length must be **exactly 2**; each exercise has **exactly 3** `items` strings (sub-points **a**, **b**, **c**).
8) Do not output `topic` or `difficulty` fields.
9) Do not output per-exercise `subject` field.
10) Use numeric values for `number` when possible.

Markdown to process:
"""


EXTRACT_STRUCTURED_SOLUTIONS_PROMPT = """You extract **grading-scale / solution** content for a Romanian math exam (e.g. baccalaureate). You receive markdown produced from a PDF (e.g. Nougat). The document may include one or more subjects: Subject I → `s1`, Subject II → `s2`, Subject III → `s3`.

## Output format

Return **ONLY** valid JSON (no markdown fences, no comments, no text before or after). The top level is always an object with optional keys `s1`, `s2`, `s3` — each value is an **array** of exercises.

If the user message contains a **SOURCE SUBJECT CONSTRAINT (from filename)** block, you **must** obey it: the top-level object must contain **only** the indicated subject key (e.g. only `"s2"`), with no other subject keys, even if the markdown mentions other subjects.

## Fixed exam shape (Baccalaureate — mandatory when a subject key is present)

- **`s1`:** output **exactly 6** exercise objects (numbers 1 through 6 in order).
- **`s2` and `s3`:** each must contain **exactly 2** exercise objects; each exercise has **`item_solutions` with exactly 3 blocks** with `item` values **`a`**, **`b`**, and **`c`** (one scoring block per sub-point).

## Schema by subject

### Subject I (`s1`)

- Each element in `s1` is an object with **exactly** these fields: `number`, `solution_steps`.
- **`solution_steps` (Subject I)** must be a single **string** (not a list). It holds the full solution / grading text for that exercise (may span paragraphs; preserve source order).
- Do **not** use `item_solutions` under `s1`.

### Subjects II and III (`s2`, `s3`)

- Each element in `s2` / `s3` has: `number`, `item_solutions`.
- **`item_solutions`** is a list of blocks — typically one block per sub-point **a**, **b**, **c** (usually three blocks per exercise).
- Each block has the shape: `{"item": "a"|"b"|"c", "solution_steps": [ ... ]}`.
- **`item`**: lowercase letter (`"a"`, `"b"`, `"c"`).
- Inside each block, **`solution_steps`** (for II/III) is a **list** of objects with fixed shape: `{"step": "...", "score": <number>}`.
  - One grading-table row, one solution line, or one scored line in the source → one `{ "step", "score" }` pair.
  - **`score`** is the numeric points from the source (e.g. `0.5`, `1`, `1.5`). If the source gives no explicit score for a row, use `0` or the value clearly implied by context — **do not invent** solution text.

## Mandatory rules (quality)

1) **Faithful copy**: every `step` and the Subject I `solution_steps` string must reproduce the source **exactly** (including LaTeX, spaces, diacritics). Do not paraphrase, translate, or “fix” wording.
2) **No extra fields**: do not output `statement`, `topic`, `difficulty`, `choices`, `items` (the problem-statement sub-item list), or a per-exercise `subject` field.
3) **Only subjects present**: include only top-level keys (`s1`/`s2`/`s3`) that have real content in the given markdown (non-empty arrays). Omit a key entirely if that subject is absent.
4) **`number`**: integer exercise index (1, 2, …) aligned with the document.
5) **Strict JSON**: double-quoted keys and strings; escape backslashes and quotes inside string values per JSON rules.

## LaTeX and mathematical notation (critical — character-by-character)

All mathematics and LaTeX appearing in the source markdown must be copied **character-by-character** into the JSON strings below. **Do not** rewrite, simplify, re-typeset, normalize, or “pretty-print” formulas.

**Where this applies:**

- **Subject I:** the entire `solution_steps` string must contain the same LaTeX sequences, delimiters (`$...$`, `\\(...\\)`, `\\[...\\]`, etc.), commands (`\\frac`, `\\int`, `\\lim`, `\\mathbb`, etc.), subscripts/superscripts, and spacing as in the source, in the same order.
- **Subjects II and III:** for each object in `item_solutions`, every `step` string must copy the corresponding line or table cell from the source **verbatim**, including full LaTeX. Each scoring row in the barem → one `{ "step": "...", "score": ... }`; the `step` text is a **literal transcription** of that row’s mathematical text.
**Hard rules:** no alternate notation for the same idea (e.g. do not replace `\\frac{a}{b}` with `a/b`), no translation of symbols, no added or removed backslashes except what JSON string escaping requires (inside JSON, a single backslash from the source often becomes `\\\\` — the **logical** characters must still match the source after parsing).

## Forbidden output shapes (the pipeline validates JSON — these will be rejected)

- **Never** set `s1`, `s2`, or `s3` to a **string** or to a **single nested object**. Each must be a **JSON array** `[...]` of exercise objects.
- **Never** use generic quiz / Q&A shapes: `questions`, `questionId`, `problem`+`solution` pairs, `id`+`question`+`answer`+`explanation`, or English placeholder text unrelated to the source.
- **Never** output only metadata like `{"subject":"s2"}` or `{"s3":{"filename":"..."}}` — you must include real exercise arrays.
- **Never** nest sub-points as object keys under the subject (e.g. `"s3": { "c": { ... } }`). Use **`item_solutions`** with `"item": "a"|"b"|"c"` instead.
- **Never** invent a different schema (e.g. `name`/`integral`/`limit` objects) — map content into `solution_steps` / `step`+`score` only.

## Illustrative example (structure only — do not copy placeholder text; respond with raw JSON, no triple-backtick blocks)

Expected shape (keys and types). Replace strings with real content from the markdown below:

{
  "s1": [
    {"number": 1, "solution_steps": "..."},
    {"number": 2, "solution_steps": "..."},
    {"number": 3, "solution_steps": "..."},
    {"number": 4, "solution_steps": "..."},
    {"number": 5, "solution_steps": "..."},
    {"number": 6, "solution_steps": "..."}
  ],
  "s2": [
    {
      "number": 1,
      "item_solutions": [
        {
          "item": "a",
          "solution_steps": [
            {"step": "First grading row or step for point a.", "score": 0.5},
            {"step": "Second row for point a.", "score": 0.5}
          ]
        },
        {
          "item": "b",
          "solution_steps": [
            {"step": "Step for b.", "score": 1}
          ]
        },
        {
          "item": "c",
          "solution_steps": [
            {"step": "Step for c.", "score": 1}
          ]
        }
      ]
    },
    {
      "number": 2,
      "item_solutions": [
        {"item": "a", "solution_steps": [{"step": "...", "score": 0.5}]},
        {"item": "b", "solution_steps": [{"step": "...", "score": 0.5}]},
        {"item": "c", "solution_steps": [{"step": "...", "score": 1}]}
      ]
    }
  ],
  "s3": [
    {
      "number": 1,
      "item_solutions": [
        {"item": "a", "solution_steps": [{"step": "...", "score": 0.25}]},
        {"item": "b", "solution_steps": [{"step": "...", "score": 0.25}]},
        {"item": "c", "solution_steps": [{"step": "...", "score": 0.5}]}
      ]
    },
    {
      "number": 2,
      "item_solutions": [
        {"item": "a", "solution_steps": [{"step": "...", "score": 0.25}]},
        {"item": "b", "solution_steps": [{"step": "...", "score": 0.25}]},
        {"item": "c", "solution_steps": [{"step": "...", "score": 0.5}]}
      ]
    }
  ]
}

**Note:** You may output only one subject key (e.g. only `s1`). When you output a subject, its array must use the **full** lengths above (6 / 2 / 2) and S2/S3 exercises must each include **three** `item_solutions` blocks (`a`, `b`, `c`).

Markdown to process:
"""


def format_structured_solutions_repair_user_message(
    *,
    validation_error: str,
    previous_raw: str,
    markdown_source: str,
    stem_hint: str | None,
    max_previous_chars: int = 12000,
) -> str:
    """
    Build a second-pass user message asking the model to fix invalid solutions JSON.

    Args:
        validation_error: Pydantic / parser error text from the first attempt.
        previous_raw: Raw model output from the failed attempt (may be truncated).
        markdown_source: Same markdown as the first extraction call.
        stem_hint: Optional ``s1``/``s2``/``s3`` from filename; adds the same constraint block if set.
        max_previous_chars: Cap on ``previous_raw`` length to keep requests bounded.

    Returns:
        Full user message for a follow-up ``/api/chat`` call.
    """
    trimmed = (previous_raw or "").strip()
    if len(trimmed) > max_previous_chars:
        trimmed = trimmed[:max_previous_chars] + "\n... [truncated]"

    stem_block = ""
    if stem_hint is not None:
        stem_block = (
            "\nSOURCE SUBJECT CONSTRAINT (from filename) — still applies:\n"
            f"{stem_hint}\n"
            "You MUST output only top-level key "
            f'"{stem_hint}" '
            "with a JSON array value.\n"
        )

    return (
        "Your previous JSON was rejected by the schema validator. Return ONLY corrected JSON "
        "(no markdown fences, no commentary).\n\n"
        f"Validation error:\n{validation_error}\n\n"
        "Required shape:\n"
        "- Top level: object with optional keys s1, s2, s3 only.\n"
        "- Each of s1/s2/s3 MUST be an array of exercise objects (never a string, never a bare object).\n"
        "- s1 element: {\"number\": int, \"solution_steps\": str} — solution_steps is ONE string.\n"
        "- s2/s3 element: {\"number\": int, "
        '"item_solutions": [{"item": "a"|"b"|"c", '
        '"solution_steps": [{"step": str, "score": number}, ...]}]}\n'
        "- Counts (Baccalaureate): if `s1` is present it must have **6** exercises; "
        "if `s2` or `s3` is present that array must have **2** exercises; each S2/S3 exercise must have "
        "**3** `item_solutions` blocks (a, b, c).\n"
        "- Do NOT use: questions[], questionId, id+answer, subject-only objects, or nested keys like "
        '"s3": {"c": ...}.\n'
        "- LaTeX / math: copy all formulas in `solution_steps` and in each `step` under `item_solutions` "
        "**character-by-character** from the markdown; do not reformat or substitute notation.\n\n"
        "Your invalid output was:\n---\n"
        f"{trimmed}\n"
        "---"
        f"{stem_block}\n"
        "Re-read the markdown below and output valid JSON only.\n\n"
        "---\n\n"
        f"{markdown_source}"
    )
