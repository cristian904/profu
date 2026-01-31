#!/usr/bin/env python3
"""
CLI for parsing bacalaureat exam PDFs with Gemini 2.0 Vision and extracting structured JSON.
Usage:
  poetry run python run.py <path_to.pdf> [--output FILE]
  poetry run python run.py --batch <downloads_dir>
  poetry run python run.py --structured <path_to.md_or_dir>
  poetry run python run.py --reclassify-difficulty <path_to.json_or_dir>
  poetry run python run.py --help

Run from backend/exam_parser so that parsers resolve.
"""
import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

_SCRIPT_DIR = Path(__file__).resolve().parent
if _SCRIPT_DIR != Path.cwd():
    sys.path.insert(0, str(_SCRIPT_DIR))

from parsers.gemini_vision_parser import parse_with_gemini_vision
from parsers.vision_to_structured import extract_structured_problems
from parsers.difficulty_rules import reclassify_structured_data


def _run_reclassify_difficulty(path: Path) -> None:
    """Reclassify difficulty for all problems in JSON file(s) using criteria-based rules."""
    if path.is_file():
        if path.suffix.lower() != ".json":
            sys.exit(f"Expected .json file, got: {path.suffix}")
        json_files = [path]
    elif path.is_dir():
        json_files = sorted(path.glob("*.json"))
    else:
        sys.exit(f"Not a file or directory: {path}")
    if not json_files:
        print("No .json files found.")
        return
    from tqdm import tqdm
    ok = 0
    for json_path in tqdm(json_files, unit="json"):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            reclassify_structured_data(data)
            json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            ok += 1
        except Exception as e:
            tqdm.write(f"ERROR {json_path.name}: {e}")
    print(f"Done. {ok}/{len(json_files)} JSON files updated (difficulty reclassified).")


def _run_structured(path: Path) -> None:
    """Run structured extraction: path is a single .md file or a folder (downloads)."""
    if path.is_file():
        if path.suffix.lower() != ".md":
            sys.exit(f"Expected .md file, got: {path.suffix}")
        downloads = path.parent.parent if path.parent.name == "vision_outputs" else path.parent
        md_files = [path]
    elif path.is_dir():
        # If user passed vision_outputs, write to parent (downloads)/structured_output per plan.
        downloads = path.parent if path.name == "vision_outputs" else path
        vision_dir = path / "vision_outputs"
        md_in_dir = list(path.glob("*.md"))
        md_in_vision = list(vision_dir.glob("*.md")) if vision_dir.is_dir() else []
        seen = {p.resolve() for p in md_in_dir}
        md_files = sorted(md_in_dir + [p for p in md_in_vision if p.resolve() not in seen])
    else:
        sys.exit(f"Not a file or directory: {path}")
    # Only process files whose path contains "statement" (e.g. *_statement.md); skip solution files etc.
    md_files = [p for p in md_files if "statement" in p.name.lower()]
    if not md_files:
        print("No .md files found (only files with 'statement' in the name are processed).")
        return
    output_dir = downloads / "structured_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    from tqdm import tqdm
    ok = 0
    for md_path in tqdm(md_files, unit="md"):
        try:
            data = extract_structured_problems(md_path)
            out_path = output_dir / f"{md_path.stem}.json"
            out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            ok += 1
        except Exception as e:
            tqdm.write(f"ERROR {md_path.name}: {e}")
    print(f"Done. {ok}/{len(md_files)} JSON files in: {output_dir}")


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
    parser.add_argument(
        "--structured",
        "-s",
        type=Path,
        metavar="PATH",
        default=None,
        help="Extract structured JSON from .md file or folder; outputs go to downloads/structured_output",
    )
    parser.add_argument(
        "--reclassify-difficulty",
        "-r",
        type=Path,
        metavar="PATH",
        default=None,
        help="Reclassify difficulty (low/medium/high) for JSON file or folder using criteria-based rules",
    )
    args = parser.parse_args()

    if args.reclassify_difficulty is not None:
        _run_reclassify_difficulty(args.reclassify_difficulty.resolve())
        return

    if args.structured is not None:
        _run_structured(args.structured.resolve())
        return

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
        parser.error("Provide pdf_path, --batch DIR, --structured PATH, or --reclassify-difficulty PATH")
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
