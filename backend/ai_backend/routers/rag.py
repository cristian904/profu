"""
RAG router: similar exam problems via vector search (shared by Rezolvare and Simulari clients).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from ai_backend.config import settings
from profu_logging.feature_logger import get_feature_logger
from ai_backend.services.rag import (
    SuggestProblemRequest,
    SuggestProblemResponse,
    run_similar_problem_suggest,
)
from .common import (
    get_current_user_id,
    get_supabase_client,
    is_solve_quota_exceeded,
)

# Same quota policy as solve-problem (monthly solve cap)
QUOTA_LIMIT_MESSAGE = (
    "Ai atins limita lunară de probleme pe care le poți rezolva cu Profu. "
    "Revino luna viitoare pentru mai multe."
)

router = APIRouter(prefix="/rag", tags=["rag"])

LOG_RAG_SUGGEST = get_feature_logger(source="rag_suggest")


@router.post("/suggest-problem", response_model=SuggestProblemResponse)
async def suggest_problem(
    body: SuggestProblemRequest,
    user_id: UUID = Depends(get_current_user_id),
    supabase=Depends(get_supabase_client),
) -> SuggestProblemResponse:
    """
    Vector search in documents table; return top similar problem statements.

    Used from Rezolvare problemă ("probleme similare") and Simulari (per-problem icon).
    Requires Authorization: Bearer <Supabase JWT>. Enforces monthly solve quota when enabled.
    """
    problem_text = (body.problem_text or "").strip()
    if not problem_text:
        raise HTTPException(status_code=400, detail="problem_text is required and cannot be empty")

    threshold = getattr(settings, "solve_monthly_quota_threshold", 0) or 0
    if is_solve_quota_exceeded(user_id, supabase, threshold):
        LOG_RAG_SUGGEST.info(
            f"Quota exceeded for rag suggest-problem: user={user_id} threshold={threshold}",
            user_id=user_id,
        )
        raise HTTPException(status_code=403, detail=QUOTA_LIMIT_MESSAGE)

    return run_similar_problem_suggest(
        problem_text=problem_text,
        supabase=supabase,
        user_id=user_id,
        match_count=5,
    )
