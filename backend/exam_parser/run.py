#!/usr/bin/env python3
"""
CLI for parsing bacalaureat exam PDFs with Gemini 2.0 Vision.
Usage:
  poetry run python run.py <path_to.pdf> [--output FILE]
  poetry run python run.py --batch <downloads_dir>
  poetry run python run.py --help

Run from backend/exam_parser so that parsers resolve.
"""
import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

_SCRIPT_DIR = Path(__file__).resolve().parent
if _SCRIPT_DIR != Path.cwd():
    sys.path.insert(0, str(_SCRIPT_DIR))

from parsers.gemini_vision_parser import parse_with_gemini_vision


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse exam PDFs with Gemini 2.0 Vision; output markdown with LaTeX math."
    )
    parser.add_argument(
        "pdf_path",
        type=Path,
        nargs="?",
        default=None,
        help="Path to a single PDF (omit when using --batch)",
    )
    parser.add_argument(
        "--batch",
        "-b",
        type=Path,
        metavar="DIR",
        default=None,
        help="Run on all PDFs in DIR; outputs go to DIR/vision_outputs as .md",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output path for single-file mode (default: same dir as PDF, {stem}.md)",
    )
    args = parser.parse_args()

    if args.batch is not None:
        downloads_dir = args.batch.resolve()
        if not downloads_dir.is_dir():
            parser.error(f"Not a directory: {downloads_dir}")
        output_dir = downloads_dir / "vision_outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        all_pdfs = sorted(downloads_dir.glob("*.pdf"))
        pdfs = [p for p in all_pdfs if not (output_dir / f"{p.stem}.md").exists()]
        if not all_pdfs:
            print(f"No PDFs found in {downloads_dir}")
            return
        if not pdfs:
            print(f"All {len(all_pdfs)} PDFs already have outputs in {output_dir}")
            return
        from tqdm import tqdm

        print(f"Running Gemini Vision on {len(pdfs)} PDFs (skipping {len(all_pdfs) - len(pdfs)} existing) → {output_dir}")
        for pdf_path in tqdm(pdfs, unit="pdf"):
            try:
                text = parse_with_gemini_vision(pdf_path)
                out_path = output_dir / f"{pdf_path.stem}.md"
                out_path.write_text(text, encoding="utf-8")
            except Exception:
                tqdm.write(f"ERROR: {pdf_path.name}")
        print(f"Done. Outputs in: {output_dir}")
        return

    if args.pdf_path is None:
        parser.error("Provide pdf_path or --batch DIR")
    pdf_path = args.pdf_path.resolve()
    if not pdf_path.is_file():
        parser.error(f"File not found: {pdf_path}")

    output_path = args.output
    if output_path is None:
        output_path = pdf_path.parent / f"{pdf_path.stem}.md"
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    text = parse_with_gemini_vision(pdf_path)
    output_path.write_text(text, encoding="utf-8")
    print(f"Done. Output: {output_path}")


if __name__ == "__main__":
    main()
