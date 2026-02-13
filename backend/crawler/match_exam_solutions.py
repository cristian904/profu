#!/usr/bin/env python3
"""
Match exam (var/statement) JSON files with scoring-scale (bar/barem) JSON files,
merge solution_steps into the exam structure, and write combined JSONs.

Output defaults to parent/structured_output_merged/ (e.g. downloads_exams/structured_output_merged/).

Single pair:
  python match_exam_solutions.py --exam path/to/exam.json --solution path/to/solution.json [--output path]

Batch:
  python match_exam_solutions.py --exams-dir path/to/structured_output --solutions-dir path/to/structured_output_solutions [--output-dir path]
"""
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from tqdm import tqdm


# --- Stem matching (exam var/varianta <-> solution bar/barem) ---

_VAR_TO_BAR_REPLACEMENTS = [
    # Order matters: longer phrases first
    (re.compile(r"var_simulare", re.IGNORECASE), "bar_simulare"),
    (re.compile(r"var_model", re.IGNORECASE), "bar_model"),
    (re.compile(r"varianta_model", re.IGNORECASE), "barem_model"),
    (re.compile(r"varianta_simulare", re.IGNORECASE), "bar_simulare"),
    (re.compile(r"_varianta_", re.IGNORECASE), "_barem_"),
    (re.compile(r"_var_", re.IGNORECASE), "_bar_"),
    # Trailing or standalone (e.g. ..._var.json stem)
    (re.compile(r"_varianta$", re.IGNORECASE), "_barem"),
    (re.compile(r"_var$", re.IGNORECASE), "_bar"),
    # variante-mate.ro: statement (exam) <-> solution
    (re.compile(r"_statement", re.IGNORECASE), "_solution"),
]

_BAR_TO_VAR_REPLACEMENTS = [
    (re.compile(r"bar_simulare", re.IGNORECASE), "var_simulare"),
    (re.compile(r"bar_model", re.IGNORECASE), "var_model"),
    (re.compile(r"barem_model", re.IGNORECASE), "varianta_model"),
    (re.compile(r"_barem_", re.IGNORECASE), "_varianta_"),
    (re.compile(r"_bar_", re.IGNORECASE), "_var_"),
    (re.compile(r"_barem$", re.IGNORECASE), "_varianta"),
    (re.compile(r"_bar$", re.IGNORECASE), "_var"),
    (re.compile(r"_solution", re.IGNORECASE), "_statement"),
]


def exam_stem_to_solution_stem(exam_stem: str) -> str:
    """Derive the solution (bar/barem) stem from an exam (var/varianta) stem."""
    result = exam_stem
    for pattern, repl in _VAR_TO_BAR_REPLACEMENTS:
        result = pattern.sub(repl, result)
    return result


def solution_stem_to_exam_stem(solution_stem: str) -> str:
    """Derive the exam (var/varianta) stem from a solution (bar/barem) stem."""
    result = solution_stem
    for pattern, repl in _BAR_TO_VAR_REPLACEMENTS:
        result = pattern.sub(repl, result)
    return result


def get_solution_stem_for_exam(exam_stem: str, solution_stems: list[str]) -> str | None:
    """
    Find a solution file stem that matches the given exam stem.
    Uses case-insensitive comparison; returns the first matching solution stem as found on disk.
    """
    candidate = exam_stem_to_solution_stem(exam_stem)
    candidate_lower = candidate.lower()
    # Prefer exact match (case-insensitive)
    for s in solution_stems:
        if s.lower() == candidate_lower:
            return s
    # Fallback: normalized key match (in case of suffix variants like LRO vs lro vs LRO-1)
    exam_key = _normalized_key(exam_stem, is_exam=True)
    for s in solution_stems:
        if _normalized_key(s, is_exam=False) == exam_key:
            return s
    return None


def _normalized_key(stem: str, *, is_exam: bool) -> str:
    """Single comparable key for matching. Both exam and solution map to same key for a pair."""
    s = stem.lower()
    if is_exam:
        for pattern, repl in _VAR_TO_BAR_REPLACEMENTS:
            s = pattern.sub(repl.lower(), s)
    else:
        for pattern, repl in _BAR_TO_VAR_REPLACEMENTS:
            s = pattern.sub(repl.lower(), s)
    # Normalize common suffix variants to one
    s = re.sub(r"[-_]?lro\d*$", "_lro", s)
    return s


def _is_exam_stem(stem: str) -> bool:
    """True if this stem looks like an exam (statement/var/varianta), not a solution (solution/bar)."""
    lower = stem.lower()
    if "solution" in lower or "bar" in lower or "barem" in lower:
        return False
    return "statement" in lower or "_var" in lower or "varianta" in lower


# --- Merge logic ---


def _norm_num(n: Any) -> str:
    """Normalize exercise number to string for comparison."""
    if n is None:
        return ""
    return str(int(n)) if isinstance(n, (int, float)) else str(n).strip()


def merge_exam_with_solution(exam_data: dict, solution_data: dict) -> dict:
    """
    Merge solution_steps from solution_data into exam_data by subject, exercise number, and item.
    Returns a new dict; only keys present in exam_data are included.
    """
    result: dict[str, Any] = {}
    for subj in ("s1", "s2", "s3"):
        if subj not in exam_data or not isinstance(exam_data[subj], list):
            continue
        exam_list = exam_data[subj]
        sol_list = solution_data.get(subj)
        if not isinstance(sol_list, list):
            sol_list = []
        if subj == "s1":
            merged = _merge_s1(exam_list, sol_list)
        else:
            merged = _merge_s2_s3(exam_list, sol_list)
        result[subj] = merged
    return result


def _merge_s1(exam_list: list[dict], sol_list: list[dict]) -> list[dict]:
    out = []
    sol_by_num = {_norm_num(s.get("number")): s for s in sol_list}
    for ex in exam_list:
        entry = dict(ex)
        num = _norm_num(ex.get("number"))
        sol = sol_by_num.get(num)
        entry["solution_steps"] = sol["solution_steps"] if sol else []
        out.append(entry)
    return out


def _merge_s2_s3(exam_list: list[dict], sol_list: list[dict]) -> list[dict]:
    # Build (number, item) -> solution entry
    sol_by_num_item: dict[tuple[str, str], dict] = {}
    for s in sol_list:
        num = _norm_num(s.get("number"))
        item = (s.get("item") or "").strip().lower()
        if not item and isinstance(s.get("item"), str):
            item = s.get("item", "").strip().lower()
        if num or item:
            sol_by_num_item[(num, item)] = s
    out = []
    item_letters = ("a", "b", "c", "d")
    for ex in exam_list:
        entry = dict(ex)
        num = _norm_num(ex.get("number"))
        items = ex.get("items")
        if not isinstance(items, list):
            items = []
        item_solutions = []
        for i, _ in enumerate(items):
            letter = item_letters[i] if i < len(item_letters) else chr(ord("a") + i)
            sol = sol_by_num_item.get((num, letter))
            item_solutions.append({
                "item": letter,
                "solution_steps": sol["solution_steps"] if sol else [],
            })
        entry["item_solutions"] = item_solutions
        out.append(entry)
    return out


# --- I/O and CLI ---


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run_single(
    exam_path: Path,
    solution_path: Path,
    output_path: Path | None,
    *,
    overwrite: bool = True,
) -> None:
    if not exam_path.is_file():
        sys.exit(f"Exam file not found: {exam_path}")
    if not solution_path.is_file():
        sys.exit(f"Solution file not found: {solution_path}")
    if output_path is not None:
        out = output_path
    else:
        # Default: parent of exam's folder / structured_output_merged / stem_merged.json
        out_dir = exam_path.parent.parent / "structured_output_merged"
        out = out_dir / f"{exam_path.stem}_merged.json"
    if out.exists() and not overwrite:
        print(f"Skip (exists): {out}", flush=True)
        return
    exam_data = load_json(exam_path)
    solution_data = load_json(solution_path)
    merged = merge_exam_with_solution(exam_data, solution_data)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"Wrote: {out}", flush=True)


def run_batch(
    exams_dir: Path,
    solutions_dir: Path,
    output_dir: Path | None,
    *,
    overwrite: bool = True,
) -> None:
    if not exams_dir.is_dir():
        sys.exit(f"Exams directory not found: {exams_dir}")
    if not solutions_dir.is_dir():
        sys.exit(f"Solutions directory not found: {solutions_dir}")
    out_dir = output_dir or (exams_dir.parent / "structured_output_merged")
    out_dir.mkdir(parents=True, exist_ok=True)
    solution_stems = [p.stem for p in solutions_dir.glob("*.json")]
    all_exam_files = sorted(exams_dir.glob("*.json"))
    # Only process files that are exams (statement/var/varianta), not solution/bar files
    exam_files = [p for p in all_exam_files if _is_exam_stem(p.stem)]
    done = 0
    skipped = 0
    for exam_path in tqdm(exam_files, unit="exam", desc="Merge"):
        stem = exam_path.stem
        sol_stem = get_solution_stem_for_exam(stem, solution_stems)
        if sol_stem is None:
            tqdm.write(f"No solution for: {exam_path.name}")
            skipped += 1
            continue
        solution_path = solutions_dir / f"{sol_stem}.json"
        if not solution_path.is_file():
            tqdm.write(f"Solution file missing: {solution_path}")
            skipped += 1
            continue
        out_path = out_dir / f"{stem}_merged.json"
        if out_path.exists() and not overwrite:
            skipped += 1
            continue
        try:
            exam_data = load_json(exam_path)
            solution_data = load_json(solution_path)
            merged = merge_exam_with_solution(exam_data, solution_data)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(merged, f, indent=2, ensure_ascii=False)
            done += 1
        except (json.JSONDecodeError, OSError) as e:
            tqdm.write(f"ERROR {exam_path.name}: {e}")
    print(f"Done. Merged: {done}, skipped: {skipped}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Match exam JSONs with solution JSONs and write merged files.",
    )
    parser.add_argument("--exam", type=Path, help="Path to a single exam JSON (single mode)")
    parser.add_argument("--solution", type=Path, help="Path to a single solution JSON (single mode)")
    parser.add_argument("--output", type=Path, help="Output path (single mode); default: parent/structured_output_merged/stem_merged.json")
    parser.add_argument(
        "--exams-dir",
        type=Path,
        metavar="DIR",
        help="Directory of exam JSONs (batch mode)",
    )
    parser.add_argument(
        "--solutions-dir",
        type=Path,
        metavar="DIR",
        help="Directory of solution JSONs (batch); default: structured_output_solutions next to exams-dir",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        metavar="DIR",
        help="Output directory (batch); default: exams-dir's parent/structured_output_merged",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Do not overwrite existing merged files",
    )
    args = parser.parse_args()

    single = args.exam is not None or args.solution is not None
    if single:
        if not args.exam or not args.solution:
            parser.error("Single mode requires both --exam and --solution")
        run_single(
            args.exam.resolve(),
            args.solution.resolve(),
            args.output.resolve() if args.output else None,
            overwrite=not args.no_overwrite,
        )
        return

    if args.exams_dir is None:
        parser.error("Provide either (--exam and --solution) or --exams-dir")
    exams_dir = args.exams_dir.resolve()
    solutions_dir = args.solutions_dir.resolve() if args.solutions_dir else (exams_dir.parent / "structured_output_solutions")
    run_batch(
        exams_dir,
        solutions_dir,
        args.output_dir.resolve() if args.output_dir else None,
        overwrite=not args.no_overwrite,
    )


if __name__ == "__main__":
    main()
