"""Load merged structured markdown into Supabase ``exam_problems`` table."""
from __future__ import annotations

import os
import re
import traceback
from typing import Any

from profu_logging.feature_logger import FeatureLogger

from exam_parser.pipeline.config import Checkpoint, PipelineConfig, RunDirs
from exam_parser.parsers.structured_markdown import (
    merged_document_to_rows_dict,
    parse_merged_markdown,
)

STEP_NAME = "load_to_db"

SUBJECT_KEY_TO_NUMBER = {"s1": 1, "s2": 2, "s3": 3}
YEAR_IN_NAME = re.compile(r"(?:^|_)(\d{4})(?:_|$)")
YEAR_FALLBACK = re.compile(r"(20\d{2})")


def _parse_year(stem: str) -> int | None:
    m = YEAR_IN_NAME.search(stem)
    if m:
        return int(m.group(1))
    m = YEAR_FALLBACK.search(stem)
    if m:
        return int(m.group(1))
    return None


def _json_to_rows(data: dict, *, year: int | None, source: str) -> list[dict]:
    """Convert one merged JSON to a list of ``exam_problems`` row dicts."""
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
            if key == "s1":
                solution = problem.get("solution_steps")
            else:
                solution = problem.get("item_solutions")
            if solution is None:
                solution = "" if key == "s1" else []
            rows.append({
                "subject_number": subject_number,
                "problem_number": num,
                "choices": [],
                "items": problem.get("items") or [],
                "topic": problem.get("topic"),
                "school_subject": "mate",
                "difficulty": problem.get("difficulty"),
                "source": source,
                "year": year,
                "statement": problem.get("statement"),
                "solution": solution,
            })
    return rows


def _get_supabase_client() -> Any:
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(url, key)


async def run(
    config: PipelineConfig,
    dirs: RunDirs,
    checkpoint: Checkpoint,
    logger: FeatureLogger,
) -> None:
    """Load all merged markdown files from ``03_merged`` into the exam_problems table."""
    merged_files = sorted(dirs.merged.glob("*_merged.md"))
    if not merged_files:
        logger.warning(f"[{STEP_NAME}] No merged markdown files found in {dirs.merged}")
        return

    pending = [f for f in merged_files if not checkpoint.is_file_done(STEP_NAME, f.name)]
    logger.info(
        f"[{STEP_NAME}] {len(merged_files)} merged JSONs, "
        f"{len(merged_files) - len(pending)} already loaded, "
        f"{len(pending)} to process"
    )

    if not pending:
        return

    if config.dry_run:
        total_rows = 0
        for f in pending:
            doc = parse_merged_markdown(f.read_text(encoding="utf-8"))
            data = merged_document_to_rows_dict(doc)
            rows = _json_to_rows(data, year=_parse_year(f.stem), source=config.source)
            total_rows += len(rows)
            logger.info(f"[DRY RUN] {f.name} → {len(rows)} rows")
        logger.info(f"[DRY RUN] Total: {total_rows} rows would be inserted")
        return

    client = _get_supabase_client()
    total_inserted = 0

    for f in pending:
        try:
            doc = parse_merged_markdown(f.read_text(encoding="utf-8"))
            data = merged_document_to_rows_dict(doc)
            year = _parse_year(f.stem)
            rows = _json_to_rows(data, year=year, source=config.source)
            if rows:
                client.table("exam_problems").insert(rows).execute()
                total_inserted += len(rows)
                logger.info(f"Inserted {len(rows)} rows from {f.name}")
            checkpoint.mark_file_done(STEP_NAME, f.name)
        except Exception as exc:
            logger.error(exc, traceback=traceback.format_exc())
            raise

    checkpoint.mark_step_done(STEP_NAME)
    logger.info(f"[{STEP_NAME}] Step complete — inserted {total_inserted} rows total")
