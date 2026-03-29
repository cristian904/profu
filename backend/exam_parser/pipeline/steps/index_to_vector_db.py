"""Step 6 — Index exam_problems into the ``documents`` vector table."""
from __future__ import annotations

import asyncio
import json
import math
import os
import traceback
from typing import Any

from profu_logging.feature_logger import FeatureLogger

from exam_parser.pipeline.config import Checkpoint, PipelineConfig, RunDirs
from exam_parser.pipeline.settings import settings

STEP_NAME = "index_to_vector_db"

EMBED_DIM = 1024
METADATA_KEYS = (
    "id",
    "subject_number",
    "problem_number",
    "choices",
    "items",
    "topic",
    "school_subject",
    "difficulty",
    "source",
    "year",
    "solution",
    "created_at",
)


def _to_serializable(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, (dict, list)):
        return json.loads(
            json.dumps(obj, default=lambda x: x.isoformat() if hasattr(x, "isoformat") else str(x))
        )
    return obj


def _build_metadata(row: dict) -> dict:
    return {k: _to_serializable(row.get(k)) for k in METADATA_KEYS if k in row}


def _normalize_embedding(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in values))
    if norm <= 0:
        return values
    return [x / norm for x in values]


def _get_supabase_client() -> Any:
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    return create_client(url, key)


def _embed_batch_sync(statements: list[str], api_key: str, model_name: str) -> list[list[float]]:
    """Embed a batch of statements with Gemini (sync)."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    result = client.models.embed_content(
        model=model_name,
        contents=statements,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBED_DIM,
            task_type="RETRIEVAL_DOCUMENT",
        ),
    )
    return [_normalize_embedding(list(emb.values)) for emb in result.embeddings]


def _fetch_exam_problems(client: Any) -> list[dict]:
    """Fetch all exam_problems with non-empty statements."""
    response = client.table("exam_problems").select("*").order("id").execute()
    return [
        row
        for row in (response.data or [])
        if row.get("statement") and isinstance(row["statement"], str) and row["statement"].strip()
    ]


async def run(
    config: PipelineConfig,
    dirs: RunDirs,
    checkpoint: Checkpoint,
    logger: FeatureLogger,
) -> None:
    """Embed all exam_problems statements and insert into documents table."""
    if checkpoint.is_step_done(STEP_NAME) and not config.overwrite:
        logger.info(f"[{STEP_NAME}] Already done, skipping")
        return

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set")

    sb_client = _get_supabase_client()
    rows = _fetch_exam_problems(sb_client)
    logger.info(f"[{STEP_NAME}] Found {len(rows)} exam_problems with statements")

    if not rows:
        checkpoint.mark_step_done(STEP_NAME)
        return

    if config.dry_run:
        logger.info(f"[DRY RUN] Would embed and index {len(rows)} rows")
        return

    # Split into chunks for the embedding API (max ~50 per call)
    chunk_size = 50
    chunks = [rows[i : i + chunk_size] for i in range(0, len(rows), chunk_size)]

    # Fire all embedding calls concurrently
    async def _embed_chunk(chunk: list[dict]) -> tuple[list[dict], list[list[float]]]:
        statements = [r["statement"] for r in chunk]
        embeddings = await asyncio.to_thread(_embed_batch_sync, statements, api_key, settings.model_embed)
        return (chunk, embeddings)

    results = await asyncio.gather(
        *[_embed_chunk(chunk) for chunk in chunks]
    )

    # Insert into documents
    total_inserted = 0
    for chunk, embeddings in results:
        if len(embeddings) != len(chunk):
            logger.warning(f"Embedding size mismatch: {len(embeddings)} vs {len(chunk)}")
            continue

        # Idempotency: remove existing documents for these exam_problem ids
        exam_problem_ids = [r["id"] for r in chunk]
        for eid in exam_problem_ids:
            try:
                existing = sb_client.table("documents").select("id").eq("metadata->>id", str(eid)).execute()
                for doc in existing.data or []:
                    sb_client.table("documents").delete().eq("id", doc["id"]).execute()
            except Exception:
                pass

        docs = [
            {
                "content": r["statement"],
                "metadata": _build_metadata(r),
                "embedding": emb,
            }
            for r, emb in zip(chunk, embeddings)
        ]
        try:
            sb_client.table("documents").insert(docs).execute()
            total_inserted += len(docs)
            logger.info(f"Inserted {total_inserted}/{len(rows)} documents")
        except Exception as exc:
            logger.error(exc, traceback=traceback.format_exc())

    checkpoint.mark_step_done(STEP_NAME)
    logger.info(f"[{STEP_NAME}] Step complete — indexed {total_inserted} documents")
