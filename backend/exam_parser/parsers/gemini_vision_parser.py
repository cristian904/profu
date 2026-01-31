"""
Parse PDF using Gemini 2.0 Vision (native PDF input), then convert to markdown/LaTeX.
"""
import os
from pathlib import Path


EXTRACT_PROMPT = (
    "Extract all text from this PDF. Preserve structure, headings, and math as LaTeX. "
    "Return as markdown only, no preamble."
)

MARKDOWN_LATEX_PROMPT = (
    "Convert the following text to clean markdown with LaTeX math: "
    "use $...$ for inline math and $$...$$ for display math. "
    "Keep headings, lists, and structure. Return only the converted text, no preamble."
)


def _to_markdown_latex(client: object, raw_text: str) -> str:
    """Ask Gemini to convert raw extracted text to markdown with LaTeX math."""
    if not raw_text.strip():
        return raw_text
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[f"{MARKDOWN_LATEX_PROMPT}\n\n---\n\n{raw_text}"],
    )
    return (response.text or "").strip()


def parse_with_gemini_vision(pdf_path: str | Path) -> str:
    """
    Convert a PDF to text using Gemini 2.0 Vision, then convert to markdown/LaTeX.
    Returns markdown-style text with $...$ and $$...$$ for math.
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
        model="gemini-2.0-flash",
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            EXTRACT_PROMPT,
        ],
    )
    raw_text = (response.text or "").strip()
    return _to_markdown_latex(client, raw_text)
