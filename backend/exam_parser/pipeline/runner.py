"""Pipeline orchestrator — runs steps in order with checkpoint awareness."""
from __future__ import annotations

from dotenv import load_dotenv

from profu_logging.feature_logger import get_feature_logger

from exam_parser.pipeline.config import (
    STEP_NAMES,
    Checkpoint,
    PipelineConfig,
    RunDirs,
)
from exam_parser.pipeline.steps import (
    fix_latex,
    index_to_vector_db,
    load_to_db,
    merge,
    parse_problems,
    parse_solutions,
)

# Ordered mapping: step_name → module (must have async ``run`` function)
STEPS = [
    ("parse_problems", parse_problems),
    ("parse_solutions", parse_solutions),
    ("merge", merge),
    ("fix_latex", fix_latex),
    ("load_to_db", load_to_db),
    ("index_to_vector_db", index_to_vector_db),
]


async def run_pipeline(config: PipelineConfig) -> None:
    """Execute the full pipeline, respecting ``start_from`` and checkpoints."""
    # Load .env from repo root
    load_dotenv()

    logger = get_feature_logger("exam_pipeline")
    dirs = RunDirs.from_config(config)
    dirs.create_all()

    checkpoint_path = dirs.root / "checkpoint.json"
    checkpoint = Checkpoint(checkpoint_path, config.run_name)

    logger.info(
        f"Pipeline started — run={config.run_name}, "
        f"problems={config.problems_dir}, solutions={config.solutions_dir}, "
        f"source={config.source}, start_from={config.start_from}, "
        f"dry_run={config.dry_run}, overwrite={config.overwrite}"
    )

    # Determine which steps to run
    start_idx = 0
    if config.start_from:
        if config.start_from not in STEP_NAMES:
            raise ValueError(
                f"Unknown step '{config.start_from}'. "
                f"Valid steps: {', '.join(STEP_NAMES)}"
            )
        start_idx = STEP_NAMES.index(config.start_from)
        # Reset checkpoint for start_from step and all subsequent steps
        for name in STEP_NAMES[start_idx:]:
            checkpoint.reset_step(name)
        logger.info(f"Resuming from step '{config.start_from}' (index {start_idx})")

    import asyncio

    pending_parallel = []

    for step_name, step_module in STEPS[start_idx:]:
        if checkpoint.is_step_done(step_name) and not config.overwrite:
            logger.info(f"Skipping step '{step_name}' — already done")
            continue

        if step_name in ("parse_problems", "parse_solutions"):
            pending_parallel.append((step_name, step_module.run(config, dirs, checkpoint, logger)))
        else:
            if pending_parallel:
                logger.info(f"=== Running parallel steps: {[n for n, _ in pending_parallel]} ===")
                await asyncio.gather(*[coro for _, coro in pending_parallel])
                logger.info(f"=== Finished parallel steps ===")
                pending_parallel = []

            logger.info(f"=== Running step: {step_name} ===")
            await step_module.run(config, dirs, checkpoint, logger)
            logger.info(f"=== Finished step: {step_name} ===")
            
    if pending_parallel:
        logger.info(f"=== Running parallel steps: {[n for n, _ in pending_parallel]} ===")
        await asyncio.gather(*[coro for _, coro in pending_parallel])
        logger.info(f"=== Finished parallel steps ===")

    logger.info("Pipeline complete")
