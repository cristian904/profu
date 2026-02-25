#!/usr/bin/env python3
"""
CLI for parsing bacalaureat exam PDFs with Gemini 2.0 Vision and extracting structured JSON.
Only processes files whose filename contains "var" or "solution" (case-insensitive).

Usage (from repo root):
  uv run python -m exam_parser.run <path_to.pdf> [--output FILE]
  uv run python -m exam_parser.run --batch <downloads_dir>
  uv run python -m exam_parser.run --structured <path_to.md_or_dir>
  uv run python -m exam_parser.run --reclassify-difficulty <path_to.json_or_dir>
  uv run python -m exam_parser.run --help
"""
import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # .env at repo root (run from repo root)

from exam_parser.parsers.gemini_vision_parser import parse_with_gemini_vision
from exam_parser.parsers.vision_to_structured import extract_structured_problems
from exam_parser.parsers.difficulty_rules import reclassify_structured_data


def _is_exam_file(path: Path) -> bool:
    """True if the file name contains 'var' or 'solution' (case-insensitive)."""
    name = path.name.lower()
    return "var_" in name or "solution" in name


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
    """Run vision (PDF→md) then structured extraction (md→JSON). Both outputs are saved."""
    if path.is_file():
        if path.suffix.lower() != ".md":
            sys.exit(f"Expected .md file, got: {path.suffix}")
        downloads = path.parent.parent if path.parent.name == "vision_outputs" else path.parent
        md_files = [path]
    elif path.is_dir():
        downloads = path.parent if path.name == "vision_outputs" else path
        vision_dir = downloads / "vision_outputs"
        md_in_dir = list(path.glob("*.md"))
        md_in_vision = list(vision_dir.glob("*.md")) if vision_dir.is_dir() else []
        seen = {p.resolve() for p in md_in_dir}
        md_files = sorted(md_in_dir + [p for p in md_in_vision if p.resolve() not in seen])
    else:
        sys.exit(f"Not a file or directory: {path}")

    # Step 1: Run vision on matching PDFs in downloads that don't have .md yet; save to vision_outputs.
    vision_dir = downloads / "vision_outputs"
    vision_dir.mkdir(parents=True, exist_ok=True)
    all_pdfs = sorted(downloads.glob("*.pdf"))
    matching_pdfs = [p for p in all_pdfs if _is_exam_file(p)]
    pdfs_to_vision = [p for p in matching_pdfs if not (vision_dir / f"{p.stem}.md").exists()]
    if pdfs_to_vision:
        from tqdm import tqdm
        for pdf_path in tqdm(pdfs_to_vision, unit="pdf", desc="Vision"):
            try:
                text = parse_with_gemini_vision(pdf_path)
                (vision_dir / f"{pdf_path.stem}.md").write_text(text, encoding="utf-8")
            except Exception as e:
                tqdm.write(f"ERROR {pdf_path.name}: {e}")
        print(f"Vision: {len(pdfs_to_vision)} PDFs → {vision_dir}")

    # Re-collect .md files when path is a directory so newly created vision outputs are included.
    if path.is_dir():
        md_in_dir = list(path.glob("*.md"))
        md_in_vision = list(vision_dir.glob("*.md")) if vision_dir.is_dir() else []
        seen = {p.resolve() for p in md_in_dir}
        md_files = sorted(md_in_dir + [p for p in md_in_vision if p.resolve() not in seen])

    # Process files with "var" or "solution" in the name; require "statement" in name only when not under vision_outputs (vision_outputs .md are exam statements by construction).
    def _is_statement_md(p: Path) -> bool:
        if not _is_exam_file(p):
            return False
        try:
            p_resolved = p.resolve()
            vision_resolved = vision_dir.resolve()
            if p_resolved == vision_resolved or vision_resolved in p_resolved.parents:
                return True  # under vision_outputs → treat as statement
        except OSError:
            pass
        return "statement" in p.name.lower()

    md_files = [p for p in md_files if _is_statement_md(p)]
    if not md_files:
        print("No .md files found (only files with 'var' or 'solution' in the name are processed; outside vision_outputs, 'statement' in the name is also required).")
        return
    output_dir = downloads  # same folder as PDFs (the dir passed to --structured)
    output_dir.mkdir(parents=True, exist_ok=True)
    from tqdm import tqdm
    ok = 0
    for md_path in tqdm(md_files, unit="md", desc="Structured"):
        try:
            data = extract_structured_problems(md_path)
            out_path = output_dir / f"{md_path.stem}.json"
            out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            ok += 1
        except Exception as e:
            tqdm.write(f"ERROR {md_path.name}: {e}")
    print(f"Done. Vision → {vision_dir}, structured → {output_dir} ({ok}/{len(md_files)} JSON files).")


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
        help="Extract structured JSON from .md file or folder; JSON files are saved in the same directory as the PDFs",
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
        matching_pdfs = [p for p in all_pdfs if _is_exam_file(p)]
        pdfs = [p for p in matching_pdfs if not (output_dir / f"{p.stem}.md").exists()]
        if not all_pdfs:
            print(f"No PDFs found in {downloads_dir}")
            return
        if not matching_pdfs:
            print(f"No PDFs with 'var' or 'solution' in the name (found {len(all_pdfs)} PDFs).")
            return
        if not pdfs:
            print(f"All {len(matching_pdfs)} matching PDFs already have outputs in {output_dir}")
            return
        from tqdm import tqdm

        print(f"Running Gemini Vision on {len(pdfs)} PDFs (skipping {len(matching_pdfs) - len(pdfs)} existing) → {output_dir}")
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
    if not _is_exam_file(pdf_path):
        parser.error("Only PDFs with 'var' or 'solution' in the filename are processed.")

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
