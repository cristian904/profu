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
    extract_problems,
    extract_solutions,
    index_to_vector_db,
    load_to_db,
    merge,
    parse_problems,
    parse_solutions,
)

# Ordered mapping: step_name → module (must have async ``run`` function)
STEPS = [
    ("extract_problems", extract_problems),
    ("parse_problems", parse_problems),
    ("extract_solutions", extract_solutions),
    ("parse_solutions", parse_solutions),
    ("merge", merge),
    ("load_to_db", load_to_db),
    ("index_to_vector_db", index_to_vector_db),
]


def _apply_model_overrides(config: PipelineConfig) -> dict[str, str]:
    """
    Temporarily patch global pipeline ``settings`` with per-run Ollama model id.

    Returns:
        Map of attribute name → previous value, for restoration in ``finally``.
    """
    from exam_parser.pipeline.settings import settings

    backup: dict[str, str] = {}
    if config.ollama_model is not None:
        backup["ollama_model"] = settings.ollama_model
        settings.ollama_model = config.ollama_model
    return backup


def _restore_model_overrides(backup: dict[str, str]) -> None:
    """Restore pipeline ``settings`` after ``run_pipeline`` finishes."""
    from exam_parser.pipeline.settings import settings

    for attr, prev in backup.items():
        setattr(settings, attr, prev)


async def run_pipeline(config: PipelineConfig) -> None:
    """Execute the full pipeline, respecting ``start_from`` and checkpoints."""
    # Load .env from repo root
    load_dotenv()

    model_backup = _apply_model_overrides(config)
    try:
        from exam_parser.pipeline.settings import settings

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
        logger.info(
            "Models / services for this run — "
            f"nougat_model={settings.nougat_model_id}, nougat_device={settings.nougat_device}, "
            f"ollama_model={settings.ollama_model}, ollama_base_url={settings.ollama_base_url}, "
            f"embed_model={settings.model_embed}"
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

        for step_name, step_module in STEPS[start_idx:]:
            if checkpoint.is_step_done(step_name) and not config.overwrite:
                logger.info(f"Skipping step '{step_name}' — already done")
                continue

            logger.info(f"=== Running step: {step_name} ===")
            await step_module.run(config, dirs, checkpoint, logger)
            logger.info(f"=== Finished step: {step_name} ===")

        logger.info("Pipeline complete")
    finally:
        _restore_model_overrides(model_backup)
