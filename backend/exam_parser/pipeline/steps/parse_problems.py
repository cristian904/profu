"""Parse problem markdown files to structured JSON using Ollama."""
from __future__ import annotations

import asyncio
import json
import traceback
from pathlib import Path

from profu_logging.feature_logger import FeatureLogger

from exam_parser.parsers.ollama_structured import (
    StructuredJsonParseError,
    extract_structured_problems_from_markdown,
)
from exam_parser.pipeline.config import Checkpoint, PipelineConfig, RunDirs
from exam_parser.pipeline.settings import settings

STEP_NAME = "parse_problems"


async def _process_one(
    pdf: Path,
    vision_dir: Path,
    structured_dir: Path,
    checkpoint: Checkpoint,
    logger: FeatureLogger,
) -> bool:
    """Read ``{stem}.md``, call Ollama, write ``{stem}.json`` structured artifact.

    Returns:
        True when parsing/writing succeeds, False when the file is skipped after an error.
    """
    stem = pdf.stem
    vision_path = vision_dir / f"{stem}.md"
    structured_out = structured_dir / f"{stem}.json"

    if not vision_path.is_file():
        logger.warning(
            f"Missing markdown for {pdf.name}; run extract_problems first. Expected: {vision_path}"
        )
        return False

    try:
        md_text = vision_path.read_text(encoding="utf-8")
        data: dict = await asyncio.to_thread(
            extract_structured_problems_from_markdown,
            md_text,
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            source_stem=stem,
        )
        structured_out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"[{STEP_NAME}] Structured JSON written: {structured_out.name}")
        checkpoint.mark_file_done(STEP_NAME, pdf.name)
        return True
    except StructuredJsonParseError as exc:
        logger.warning(
            f"[{STEP_NAME}] JSON parsing failed for file (skipping): {vision_path}"
        )
        logger.warning(
            f"[{STEP_NAME}] Raw model JSON response for {vision_path.name}:\n{exc.raw_response}"
        )
        return False
    except Exception as exc:
        logger.warning(
            f"[{STEP_NAME}] Unexpected parsing failure for file (skipping): {vision_path}"
        )
        logger.warning(f"[{STEP_NAME}] Failure details: {exc}\n{traceback.format_exc()}")
        return False


async def run(
    config: PipelineConfig,
    dirs: RunDirs,
    checkpoint: Checkpoint,
    logger: FeatureLogger,
) -> None:
    """Parse each problem PDF's markdown concurrently (Ollama local)."""
    pdfs = sorted(config.problems_dir.glob("*.pdf"))
    if not pdfs:
        logger.warning(f"[{STEP_NAME}] No PDFs found in {config.problems_dir}")
        return

    pending = [p for p in pdfs if not checkpoint.is_file_done(STEP_NAME, p.name)]
    logger.info(
        f"[{STEP_NAME}] {len(pdfs)} PDFs total, {len(pdfs) - len(pending)} already parsed, "
        f"{len(pending)} to process"
    )

    if not pending:
        return

    if config.dry_run:
        for p in pending:
            logger.info(f"[{STEP_NAME}] [DRY RUN] Would parse via Ollama: {p.name}")
        return

    tasks = [
        _process_one(pdf, dirs.problems_vision, dirs.problems_structured, checkpoint, logger)
        for pdf in pending
        if (dirs.problems_vision / f"{pdf.stem}.md").is_file()
    ]
    missing_md = [
        p.name
        for p in pending
        if not (dirs.problems_vision / f"{p.stem}.md").is_file()
    ]
    if missing_md:
        preview = ", ".join(missing_md[:5])
        extra = f" (+{len(missing_md) - 5} more)" if len(missing_md) > 5 else ""
        logger.warning(
            f"[{STEP_NAME}] Skipping {len(missing_md)} file(s) without markdown: {preview}{extra}"
        )

    if not tasks:
        logger.warning(f"[{STEP_NAME}] No markdown files to parse")
        return

    results = await asyncio.gather(*tasks)
    parsed_count = 0
    skipped_count = len(missing_md)
    for ok in results:
        if ok:
            parsed_count += 1
        else:
            skipped_count += 1
    unresolved = [p.name for p in pending if not checkpoint.is_file_done(STEP_NAME, p.name)]
    if unresolved:
        preview = ", ".join(unresolved[:5])
        extra = f" (+{len(unresolved) - 5} more)" if len(unresolved) > 5 else ""
        logger.error(
            f"[{STEP_NAME}] Step failed — {len(unresolved)} file(s) still pending: "
            f"{preview}{extra}"
        )
        raise RuntimeError(
            f"[{STEP_NAME}] Parsing failed for {len(unresolved)} file(s); "
            "inspect step logs for details."
        )
    else:
        checkpoint.mark_step_done(STEP_NAME)
        logger.info(f"[{STEP_NAME}] Step marked done")
    logger.info(
        f"[{STEP_NAME}] Step complete — parsed: {parsed_count}, skipped: {skipped_count}, "
        f"remaining: {len(unresolved)}"
    )
