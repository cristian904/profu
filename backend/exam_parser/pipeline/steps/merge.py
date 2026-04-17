"""Step 3 — Merge problem and solution structured markdown files by matching filenames."""
from __future__ import annotations

import traceback
from typing import Any

from profu_logging.feature_logger import FeatureLogger

from exam_parser.pipeline.config import Checkpoint, PipelineConfig, RunDirs
from exam_parser.parsers.structured_markdown import (
    parse_problems_markdown,
    parse_solutions_markdown,
    serialize_merged_document,
)
from exam_parser.parsers.structured_models import MergedDocument

STEP_NAME = "merge"


# ---------------------------------------------------------------------------
# Merge helpers (adapted from crawler/match_exam_solutions.py to avoid
# cross-package dependency)
# ---------------------------------------------------------------------------

def _norm_num(n: Any) -> str:
    """Normalize exercise number to string for comparison."""
    if n is None:
        return ""
    return str(int(n)) if isinstance(n, (int, float)) else str(n).strip()


def _merge_s1(exam_list: list[dict], sol_list: list[dict]) -> list[dict]:
    sol_by_num = {_norm_num(s.get("number")): s for s in sol_list}
    out = []
    for ex in exam_list:
        entry = dict(ex)
        num = _norm_num(ex.get("number"))
        sol = sol_by_num.get(num)
        entry["solution_steps"] = (sol or {}).get("solution_steps") or ""
        out.append(entry)
    return out


def _merge_s2_s3(exam_list: list[dict], sol_list: list[dict]) -> list[dict]:
    sol_by_num = {_norm_num(s.get("number")): s for s in sol_list}
    out = []
    for ex in exam_list:
        entry = dict(ex)
        num = _norm_num(ex.get("number"))
        sol = sol_by_num.get(num) or {}
        item_solutions = sol.get("item_solutions")
        if not isinstance(item_solutions, list):
            item_solutions = []
        entry["item_solutions"] = item_solutions
        out.append(entry)
    return out


def merge_exam_with_solution(exam_data: dict, solution_data: dict) -> dict:
    """Merge solution_steps from *solution_data* into *exam_data* by subject and exercise number."""
    result: dict[str, Any] = {}
    for subj in ("s1", "s2", "s3"):
        if subj not in exam_data or not isinstance(exam_data[subj], list):
            continue
        sol_list = solution_data.get(subj)
        if not isinstance(sol_list, list):
            sol_list = []
        if subj == "s1":
            result[subj] = _merge_s1(exam_data[subj], sol_list)
        else:
            result[subj] = _merge_s2_s3(exam_data[subj], sol_list)
    return result


# ---------------------------------------------------------------------------
# Step entry point
# ---------------------------------------------------------------------------

async def run(
    config: PipelineConfig,
    dirs: RunDirs,
    checkpoint: Checkpoint,
    logger: FeatureLogger,
) -> None:
    """Match problem markdown with solution markdown by filename, merge, write merged markdown."""
    problem_mds = sorted(dirs.problems_structured.glob("*.md"))
    if not problem_mds:
        logger.warning(f"[{STEP_NAME}] No problem markdown files found in {dirs.problems_structured}")
        return

    # Build lookup of available solution files by stem
    solution_stems = {p.stem: p for p in dirs.solutions_structured.glob("*.md")}

    pending = [p for p in problem_mds if not checkpoint.is_file_done(STEP_NAME, p.name)]
    logger.info(
        f"[{STEP_NAME}] {len(problem_mds)} problem markdown files, "
        f"{len(problem_mds) - len(pending)} already merged, "
        f"{len(pending)} to process"
    )

    if not pending:
        return

    merged_count = 0
    skipped_count = 0

    for problem_path in pending:
        stem = problem_path.stem
        solution_path = solution_stems.get(stem)

        if solution_path is None:
            logger.warning(f"[{STEP_NAME}] No matching solution for: {problem_path.name}")
            skipped_count += 1
            continue

        if config.dry_run:
            logger.info(f"[DRY RUN] Would merge: {problem_path.name} + {solution_path.name}")
            continue

        try:
            exam_data = parse_problems_markdown(
                problem_path.read_text(encoding="utf-8")
            ).to_exam_dict()
            sol_data = parse_solutions_markdown(
                solution_path.read_text(encoding="utf-8")
            ).to_solution_dict()
            merged = merge_exam_with_solution(exam_data, sol_data)
            out_path = dirs.merged / f"{stem}_merged.md"
            merged_doc = MergedDocument.from_merge_dict(merged)
            out_path.write_text(serialize_merged_document(merged_doc), encoding="utf-8")
            checkpoint.mark_file_done(STEP_NAME, problem_path.name)
            merged_count += 1
        except Exception as exc:
            logger.error(exc, traceback=traceback.format_exc())
            raise

    if not config.dry_run:
        checkpoint.mark_step_done(STEP_NAME)
    logger.info(
        f"[{STEP_NAME}] Step complete — merged: {merged_count}, skipped: {skipped_count}"
    )
