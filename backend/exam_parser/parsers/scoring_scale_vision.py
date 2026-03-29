"""
Parse scoring-scale (barem/rezolvare) PDFs with Gemini 2.0 Vision.
Output is markdown with LaTeX math; document may contain one or all three subjects (I, II, III).
"""
import os
from pathlib import Path


SCORING_SCALE_EXTRACT_PROMPT = """This PDF is a Romanian bacalaureat scoring scale (barem / rezolvare). It may contain one of Subiectul I, II, or III, or all three in the same file.

Output clean, well-formed markdown:

- **Headings**: Use `#` for the main title (if any), `##` for "Subiectul I", "Subiectul II", "Subiectul III", `###` for exercise numbers (e.g. "Exercițiul 1") or item labels (e.g. "a)", "b)").
- **Scores and steps**: When there are multiple steps with different point values (e.g. 3p, 2p), do NOT put all steps first and then all scores at the end. Place each score immediately above or on the same line as the step it refers to. Use either: (a) a markdown table with one row per step (e.g. | Step | Puncte |), or (b) inline: step 1, then its score (e.g. 3p), then step 2, then its score (e.g. 2p). Order must be: step 1 → score 1 → step 2 → score 2 → … Wrong: step A, step B, 3p, 2p. Right: step A, 3p; step B, 2p (or use a table).
- **Tables**: If the barem uses tables (step description + points), render them as proper markdown tables with `|` separators and a header row (e.g. | Step | Puncte |). Use one row per scoring step.
- **Lists**: Use `-` or `*` for unordered lists and `1.` `2.` for ordered lists where appropriate. Keep list items on separate lines.
- **Math**: Format all formulas and equations in LaTeX: `$...$` for inline math, `$$...$$` for display (block) math. Preserve symbols (e.g. \\sqrt, \\frac, \\mathbb).
- **Paragraphs**: Separate paragraphs with a blank line. Do not merge distinct sections.
- **Emphasis**: Use **bold** for labels like "Exercițiul", "Subiectul" in headings if it helps structure; keep body text plain.
- **No preamble**: Return only the markdown document, no introduction or commentary."""


def parse_scoring_scale_pdf(pdf_path: str | Path, model_name: str = "gemini-2.5-flash") -> str:
    """
    Convert a scoring scale (barem) PDF to markdown using Gemini Vision.
    Extracts the solution steps corresponding to s1, s2, s3.
    Returns markdown with structure and LaTeX math ($...$ and $$...$$).
    """
    from google import genai
    from google.genai import types

    path = Path(pdf_path)
    if not path.is_file() or path.suffix.lower() != ".pdf":
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")

    pdf_bytes = path.read_bytes()
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_name,
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            SCORING_SCALE_EXTRACT_PROMPT,
        ],
    )
    return (response.text or "").strip()
