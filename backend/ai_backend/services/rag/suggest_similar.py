"""
Core logic: embed query text and fetch similar exam problem statements from Supabase.
"""

from __future__ import annotations

import traceback
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from profu_logging.log_utils import log_json

from ai_backend.services.rag.embeddings import embed_query
from ai_backend.services.rag.models import SuggestedProblemItem, SuggestProblemResponse


def run_similar_problem_suggest(
    *,
    problem_text: str,
    supabase: Any,
    user_id: UUID,
    match_count: int = 5,
) -> SuggestProblemResponse:
    """
    Embed the given text, run match_documents, and build the API response.

    Args:
        problem_text: Non-empty trimmed statement used as the retrieval query.
        supabase: Supabase client with rpc("match_documents", ...).
        user_id: Authenticated user (for structured logs).
        match_count: Number of neighbors to return (default 5).

    Returns:
        SuggestProblemResponse with Romanian message and problem list.

    Raises:
        HTTPException: On missing Supabase, embedding failure, or RPC failure.
    """
    if supabase is None:
        raise HTTPException(
            status_code=500,
            detail="SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY) must be set",
        )

    try:
        query_embedding = embed_query(problem_text)
    except HTTPException:
        raise
    except Exception as e:
        log_json(
            source="rag_suggest",
            level="error",
            message=f"Embedding failed: {e!s}",
            user_id=user_id,
            traceback=traceback.format_exc(),
        )
        raise HTTPException(
            status_code=500,
            detail="Embedding failed. Check server logs for details.",
        ) from e

    try:
        r = supabase.rpc(
            "match_documents",
            {"query_embedding": query_embedding, "match_count": match_count},
        ).execute()
        rows = (r.data or []) if hasattr(r, "data") else []
    except Exception as e:
        log_json(
            source="rag_suggest",
            level="error",
            message=f"match_documents RPC failed: {e!s}",
            user_id=user_id,
            traceback=traceback.format_exc(),
        )
        raise HTTPException(
            status_code=500,
            detail="Vector search failed. Check server logs for details.",
        ) from e

    doc_ids = [row.get("id") for row in rows]
    log_json(
        source="rag_suggest",
        level="info",
        message=f"Document ids shown to user (check in DB): {doc_ids}",
        user_id=user_id,
        traceback=None,
    )

    problems = [SuggestedProblemItem(statement=(row.get("content") or "")) for row in rows]
    if not problems:
        message = "Nu am găsit probleme similare în baza de date."
    else:
        parts = [f"{i + 1}. {p.statement}" for i, p in enumerate(problems)]
        message = "Uite " + str(len(problems)) + " probleme asemanatoare cu acesta:\n\n" + "\n\n".join(parts)

    return SuggestProblemResponse(message=message, problems=problems)
