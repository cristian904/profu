#!/usr/bin/env python3
"""
CLI for parsing scoring-scale (barem/solution) PDFs with Gemini Vision and extracting structured JSON.

Usage (from repo root):
  uv run python -m exam_parser.run_solutions <path_to.pdf_or_dir> [--output-dir DIR] [--skip-existing]
  uv run python -m exam_parser.run_solutions <directory> --rerun-null-steps
  uv run python -m exam_parser.run_solutions --help

Outputs are saved in the same folder as the PDF(s): vision_outputs_solutions/ (markdown) and structured_output_solutions/ (JSON).
With --rerun-null-steps, scans structured_output_solutions/ for JSONs with null or empty step fields and re-runs vision + structured extraction for the corresponding PDFs in the same base folder.
"""
import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # .env at repo root (run from repo root)

from exam_parser.parsers.scoring_scale_vision import parse_scoring_scale_pdf
from exam_parser.parsers.scoring_scale_to_structured import scoring_scale_md_to_structured

VISION_SUBFOLDER = "vision_outputs_solutions"
STRUCTURED_SUBFOLDER = "structured_output_solutions"


def _is_solution_or_barem(path: Path) -> bool:
    """True if the file name contains 'solution' or 'bar' (case-insensitive)."""
    name = path.name.lower()
    return "solution" in name or "bar" in name


def _has_null_or_invalid_steps(data: dict) -> bool:
    """True if any s1/s2/s3 entry has solution_steps (array) with null/empty step or missing score."""
    for key in ("s1", "s2", "s3"):
        entries = data.get(key)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            steps = entry.get("solution_steps")
            if not isinstance(steps, list):
                continue
            for item in steps:
                if not isinstance(item, dict):
                    continue
                step_val = item.get("step")
                if step_val is None or step_val == "":
                    return True
                if "score" not in item:
                    return True
    return False


def _run_rerun_null_steps(input_path: Path, output_dir: Path | None) -> None:
    """Re-run vision + structured for PDFs whose JSON has null or invalid steps."""
    if not input_path.is_dir():
        sys.exit("With --rerun-null-steps, input must be a directory containing structured_output_solutions/ and the PDFs.")

    base_dir = output_dir.resolve() if output_dir is not None else input_path
    structured_dir = base_dir / STRUCTURED_SUBFOLDER
    if not structured_dir.is_dir():
        sys.exit(f"Structured output directory not found: {structured_dir}")

    bad_stems: list[str] = []
    for json_path in structured_dir.glob("*.json"):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            if _has_null_or_invalid_steps(data):
                bad_stems.append(json_path.stem)
        except (json.JSONDecodeError, OSError):
            continue

    if not bad_stems:
        print("No JSON files with null or invalid steps found.")
        return

    pdf_files = []
    for stem in bad_stems:
        pdf_path = base_dir / f"{stem}.pdf"
        if pdf_path.is_file() and _is_solution_or_barem(pdf_path):
            pdf_files.append(pdf_path)

    if not pdf_files:
        print(f"Found {len(bad_stems)} JSON(s) with null/invalid steps but no matching PDFs (with 'solution' or 'bar' in name) in {base_dir}.")
        return

    vision_dir = base_dir / VISION_SUBFOLDER
    vision_dir.mkdir(parents=True, exist_ok=True)
    structured_dir.mkdir(parents=True, exist_ok=True)

    try:
        from tqdm import tqdm
    except ImportError:
        tqdm = None

    ok = 0
    it = tqdm(pdf_files, unit="pdf") if tqdm else pdf_files
    for pdf_path in it:
        try:
            md_text = parse_scoring_scale_pdf(pdf_path)
            vision_path = vision_dir / f"{pdf_path.stem}.md"
            vision_path.write_text(md_text, encoding="utf-8")
            data = scoring_scale_md_to_structured(md_text)
            json_path = structured_dir / f"{pdf_path.stem}.json"
            json_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            ok += 1
        except Exception as e:
            if tqdm:
                tqdm.write(f"ERROR {pdf_path.name}: {e}")
            else:
                print(f"ERROR {pdf_path.name}: {e}")

    print(f"Done. Re-ran {ok}/{len(pdf_files)} PDFs with null/invalid steps → vision: {vision_dir}, JSON: {structured_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse scoring-scale PDFs with Gemini Vision; output structured JSON (s1/s2/s3 with steps and scores).",
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to a single scoring-scale PDF or a directory containing PDFs.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=None,
        help="Base directory for outputs. If omitted, uses the folder containing the PDF(s). Creates vision_outputs_solutions/ and structured_output_solutions/ under it.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip PDFs that already have a corresponding .json in the structured output directory.",
    )
    parser.add_argument(
        "--rerun-null-steps",
        action="store_true",
        help="Scan structured_output_solutions/ for JSONs with null or empty step fields and re-run vision + structured extraction for the corresponding PDFs in the same base folder. Requires a directory as input.",
    )
    args = parser.parse_args()

    input_path = args.input_path.resolve()

    if args.rerun_null_steps:
        _run_rerun_null_steps(input_path, args.output_dir)
        return

    if input_path.is_file():
        if input_path.suffix.lower() != ".pdf":
            sys.exit(f"Expected .pdf file, got: {input_path.suffix}")
        if not _is_solution_or_barem(input_path):
            sys.exit("Only PDFs with 'solution' or 'bar' in the filename are parsed.")
        pdf_files = [input_path]
        base_dir = input_path.parent
    elif input_path.is_dir():
        all_pdfs = sorted(input_path.glob("*.pdf"))
        pdf_files = [p for p in all_pdfs if _is_solution_or_barem(p)]
        if not pdf_files:
            if not all_pdfs:
                print(f"No PDFs found in {input_path}")
            else:
                print(f"No PDFs with 'solution' or 'bar' in the name (found {len(all_pdfs)} PDFs).")
            return
        base_dir = input_path
    else:
        sys.exit(f"Not a file or directory: {input_path}")

    if args.output_dir is not None:
        base_dir = args.output_dir.resolve()
    vision_dir = base_dir / VISION_SUBFOLDER
    structured_dir = base_dir / STRUCTURED_SUBFOLDER
    vision_dir.mkdir(parents=True, exist_ok=True)
    structured_dir.mkdir(parents=True, exist_ok=True)

    if args.skip_existing:
        pdf_files = [
            p for p in pdf_files
            if not (structured_dir / f"{p.stem}.json").exists()
        ]
        if not pdf_files:
            print("All PDFs already have JSON outputs; nothing to do.")
            return

    try:
        from tqdm import tqdm
    except ImportError:
        tqdm = None

    ok = 0
    it = tqdm(pdf_files, unit="pdf") if tqdm else pdf_files
    for pdf_path in it:
        try:
            md_text = parse_scoring_scale_pdf(pdf_path)
            vision_path = vision_dir / f"{pdf_path.stem}.md"
            vision_path.write_text(md_text, encoding="utf-8")
            data = scoring_scale_md_to_structured(md_text)
            json_path = structured_dir / f"{pdf_path.stem}.json"
            json_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            ok += 1
        except Exception as e:
            if tqdm:
                tqdm.write(f"ERROR {pdf_path.name}: {e}")
            else:
                print(f"ERROR {pdf_path.name}: {e}")

    print(f"Done. {ok}/{len(pdf_files)} → vision: {vision_dir}, JSON: {structured_dir}")


if __name__ == "__main__":
    main()
