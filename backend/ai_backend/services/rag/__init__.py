"""
RAG feature: vector similarity over indexed exam problem statements.
"""

from ai_backend.services.rag.embeddings import embed_query, normalize_embedding
from ai_backend.services.rag.models import (
    SuggestedProblemItem,
    SuggestProblemRequest,
    SuggestProblemResponse,
)
from ai_backend.services.rag.suggest_similar import run_similar_problem_suggest

__all__ = [
    "embed_query",
    "normalize_embedding",
    "run_similar_problem_suggest",
    "SuggestedProblemItem",
    "SuggestProblemRequest",
    "SuggestProblemResponse",
]
