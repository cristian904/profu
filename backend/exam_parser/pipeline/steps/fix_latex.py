"""Step 4 — Validate and repair LaTeX in merged exam JSONs using Gemini Pro + Flash."""
from __future__ import annotations

import asyncio
import copy
import json
import os
import traceback
from pathlib import Path
from typing import Any

from profu_logging.feature_logger import FeatureLogger

from exam_parser.pipeline.steps.fix_latex_utils import (
    collect_latex_fields,
    evaluate_batch_pro,
    repair_with_flash,
    set_at,
)
from exam_parser.pipeline.config import Checkpoint, PipelineConfig, RunDirs
from exam_parser.pipeline.settings import settings

STEP_NAME = "fix_latex"


def _get_gemini_client() -> Any:
    """Create and return a google.genai Client."""
    from google import genai

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set")
    return genai.Client(api_key=api_key)


async def _fix_one_file(
    src: Path,
    dst: Path,
    client: Any,
    checkpoint: Checkpoint,
    logger: FeatureLogger,
) -> None:
    """Evaluate + repair all LaTeX fields in a single merged JSON."""
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            logger.warning(f"Skipping {src.name}: root is not an object")
            return

        fields = collect_latex_fields(data)
        if not fields:
            dst.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            checkpoint.mark_file_done(STEP_NAME, src.name)
            logger.info(f"No LaTeX fields in {src.name} — copied unchanged")
            return

        logger.info(f"Evaluating {len(fields)} field(s) in {src.name}")
        working = copy.deepcopy(data)

        # Evaluate all fields at once
        id_text = [(fid, txt) for fid, _path, txt in fields]
        verdict: dict[str, list[str]] = await asyncio.to_thread(
            evaluate_batch_pro, client, id_text, settings.model_fix_identify
        )

        # Collect fields that need repair
        repair_tasks: list[tuple[str, list[str | int], str, list[str]]] = []
        ok_count = 0
        for fid, path, original in fields:
            issues = verdict.get(fid)
            if issues is None:
                issues = ["Unknown evaluation failure"]
            if not issues:
                ok_count += 1
                continue
            repair_tasks.append((fid, path, original, issues))

        logger.info(
            f"{src.name}: {ok_count} OK, {len(repair_tasks)} need repair"
        )

        # Fire all repairs concurrently
        if repair_tasks:

            async def _repair(fid: str, path: list, original: str, issues: list[str]) -> tuple[str, list, str | None]:
                try:
                    fixed = await asyncio.to_thread(repair_with_flash, client, original, issues, settings.model_fix_repair)
                    return (fid, path, fixed)
                except Exception as exc:
                    logger.error(
                        f"Flash repair failed for {fid} in {src.name}: {exc}",
                        traceback=traceback.format_exc(),
                    )
                    return (fid, path, None)

            results = await asyncio.gather(
                *[_repair(fid, path, orig, iss) for fid, path, orig, iss in repair_tasks]
            )

            repaired = 0
            failed = 0
            for fid, path, fixed_text in results:
                if fixed_text is not None:
                    set_at(working, path, fixed_text)
                    repaired += 1
                else:
                    failed += 1

            logger.info(f"{src.name}: repaired={repaired}, failed={failed}")

        dst.write_text(json.dumps(working, indent=2, ensure_ascii=False), encoding="utf-8")
        checkpoint.mark_file_done(STEP_NAME, src.name)
        logger.info(f"Wrote fixed file: {dst.name}")

    except Exception as exc:
        logger.error(exc, traceback=traceback.format_exc())


async def run(
    config: PipelineConfig,
    dirs: RunDirs,
    checkpoint: Checkpoint,
    logger: FeatureLogger,
) -> None:
    """Fix LaTeX in all merged JSONs concurrently."""
    merged_files = sorted(dirs.merged.glob("*.json"))
    if not merged_files:
        logger.warning(f"[{STEP_NAME}] No merged JSONs found in {dirs.merged}")
        return

    pending = [f for f in merged_files if not checkpoint.is_file_done(STEP_NAME, f.name)]
    logger.info(
        f"[{STEP_NAME}] {len(merged_files)} merged JSONs, "
        f"{len(merged_files) - len(pending)} already fixed, "
        f"{len(pending)} to process"
    )

    if not pending:
        return

    if config.dry_run:
        for f in pending:
            logger.info(f"[DRY RUN] Would fix: {f.name}")
        return

    client = _get_gemini_client()

    tasks = [
        _fix_one_file(src, dirs.fixed / src.name, client, checkpoint, logger)
        for src in pending
    ]
    await asyncio.gather(*tasks)
    checkpoint.mark_step_done(STEP_NAME)
    logger.info(f"[{STEP_NAME}] Step complete")
