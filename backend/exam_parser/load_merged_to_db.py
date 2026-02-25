#!/usr/bin/env python3
"""
Load merged exam JSONs into Supabase Postgres (exam_problems table).

Reads all *_merged.json from a directory, parses year/source from filenames,
maps each problem to exam_problems rows, and batch-inserts via the Supabase Python client.

Usage (from repo root):
  uv run python -m exam_parser.load_merged_to_db --merged-dir <path> [--source var|exam|test] [--dry-run]
  uv run python -m exam_parser.load_merged_to_db --merged-dir backend/crawler/downloads/structured_output_merged

Requires repo root .env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (or anon key).
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

# #region agent log
DEBUG_LOG_PATH = Path(__file__).resolve().parent.parent.parent / ".cursor" / "debug.log"
def _debug_log(message: str, data: dict, hypothesis_id: str) -> None:
    try:
        payload = {"id": f"log_{hypothesis_id}", "message": message, "data": data, "hypothesisId": hypothesis_id}
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass
# #endregion

load_dotenv()  # .env at repo root (run from repo root)

# Subject key in merged JSON -> exam_problems.subject_number
SUBJECT_KEY_TO_NUMBER = {"s1": 1, "s2": 2, "s3": 3}

YEAR_IN_NAME = re.compile(r"(?:^|_)(\d{4})(?:_|$)")
YEAR_FALLBACK = re.compile(r"(20\d{2})")


def parse_year_from_stem(stem: str) -> int | None:
    """Extract 4-digit year from merged filename stem. Returns None if not found."""
    m = YEAR_IN_NAME.search(stem)
    if m:
        return int(m.group(1))
    m = YEAR_FALLBACK.search(stem)
    if m:
        return int(m.group(1))
    return None


def merged_json_to_rows(
    data: dict,
    *,
    year: int | None,
    source: str,
) -> list[dict]:
    """
    Convert one merged JSON (keys s1, s2, s3) to a list of exam_problems row dicts.
    Each row has: subject_number, problem_number, choices, items, topic, school_subject,
    difficulty, source, year, statement, solution (JSONB).
    """
    rows: list[dict] = []
    for key in ("s1", "s2", "s3"):
        if key not in data or not isinstance(data[key], list):
            continue
        subject_number = SUBJECT_KEY_TO_NUMBER[key]
        for problem in data[key]:
            if not isinstance(problem, dict):
                continue
            num = problem.get("number")
            if num is not None and not isinstance(num, int):
                try:
                    num = int(num)
                except (TypeError, ValueError):
                    num = None
            # solution: s1 -> solution_steps; s2/s3 -> item_solutions
            if key == "s1":
                solution = problem.get("solution_steps")
            else:
                solution = problem.get("item_solutions")
            if solution is None:
                solution = []
            row = {
                "subject_number": subject_number,
                "problem_number": num,
                "choices": problem.get("choices") if problem.get("choices") is not None else [],
                "items": problem.get("items") if problem.get("items") is not None else [],
                "topic": problem.get("topic"),
                "school_subject": problem.get("subject"),
                "difficulty": problem.get("difficulty"),
                "source": source,
                "year": year,
                "statement": problem.get("statement"),
                "solution": solution,
            }
            rows.append(row)
    return rows


def discover_merged_files(merged_dir: Path) -> list[Path]:
    """Return sorted list of *_merged.json paths in merged_dir."""
    if not merged_dir.is_dir():
        return []
    return sorted(merged_dir.glob("*_merged.json"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load merged exam JSONs into Supabase exam_problems table.",
    )
    parser.add_argument(
        "--merged-dir",
        type=Path,
        metavar="PATH",
        default=None,
        help="Directory containing *_merged.json files (default: ../crawler/downloads/structured_output_merged from script)",
    )
    parser.add_argument(
        "--source",
        type=str,
        choices=("var", "exam", "test"),
        default="var",
        help="exam_problems.source value (default: var)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only discover files and count rows; do not insert",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=80,
        metavar="N",
        help="Insert batch size (default: 80)",
    )
    args = parser.parse_args()

    merged_dir = args.merged_dir
    if merged_dir is None:
        merged_dir = _SCRIPT_DIR.parent / "crawler" / "downloads" / "structured_output_merged"
    merged_dir = merged_dir.resolve()

    if not merged_dir.is_dir():
        sys.exit(f"Merged directory not found: {merged_dir}")

    files = discover_merged_files(merged_dir)
    if not files:
        sys.exit(f"No *_merged.json files found in {merged_dir}")

    all_rows: list[dict] = []
    for path in files:
        stem = path.stem
        year = parse_year_from_stem(stem)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        rows = merged_json_to_rows(data, year=year, source=args.source)
        all_rows.extend(rows)

    print(f"Discovered {len(files)} merged file(s) -> {len(all_rows)} problem row(s).", flush=True)

    if args.dry_run:
        if all_rows:
            print("Sample row keys:", list(all_rows[0].keys()), flush=True)
        print("Dry run: no insert.", flush=True)
        return

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY) in .env")

    try:
        from supabase import create_client
    except ImportError:
        sys.exit("Install supabase: poetry add supabase")

    client = create_client(url, key)
    batch_size = max(1, args.batch_size)
    inserted = 0
    # #region agent log
    try:
        parsed = urlparse(url)
        _debug_log("Insert target and payload keys", {"url_host": parsed.netloc or url[:50], "first_row_keys": list(all_rows[0].keys()) if all_rows else [], "row_count": len(all_rows)}, "H1")
        _debug_log("About to insert first batch", {"batch_index": 0, "chunk_size": min(batch_size, len(all_rows)), "has_solution_key": "solution" in (all_rows[0] if all_rows else {})}, "H4")
    except Exception:
        pass
    # #endregion
    for i in range(0, len(all_rows), batch_size):
        chunk = all_rows[i : i + batch_size]
        try:
            client.table("exam_problems").insert(chunk).execute()
            inserted += len(chunk)
            print(f"Inserted {inserted}/{len(all_rows)} rows.", flush=True)
        except Exception as e:
            print(f"Insert failed at batch {i // batch_size + 1}: {e}", file=sys.stderr, flush=True)
            raise

    print(f"Done. Inserted {inserted} rows into exam_problems.", flush=True)


if __name__ == "__main__":
    main()
