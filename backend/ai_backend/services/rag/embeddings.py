"""
Embeddings helpers for RAG (similar exam problems).

Provides query embedding with Gemini embeddings and normalization.
"""

from fastapi import HTTPException

from ai_backend.config import settings


def normalize_embedding(values: list[float]) -> list[float]:
    """
    Normalize an embedding to unit length for cosine/inner-product similarity.

    Args:
        values: Raw embedding vector.

    Returns:
        Normalized embedding vector.
    """
    import math

    norm = math.sqrt(sum(x * x for x in values))
    if norm <= 0:
        return values
    return [x / norm for x in values]


def embed_query(text: str) -> list[float]:
    """
    Embed a single query string with Gemini embeddings (1024-dim, RETRIEVAL_QUERY, normalized).

    Args:
        text: Input query text to embed.

    Returns:
        Normalized embedding vector.

    Raises:
        HTTPException: When embedding fails or configuration is missing.
    """
    from google import genai
    from google.genai import types

    if not settings.google_api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not found")

    client = genai.Client(api_key=settings.google_api_key)
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=[text],
        config=types.EmbedContentConfig(
            output_dimensionality=1024,
            task_type="RETRIEVAL_QUERY",
        ),
    )
    if not result.embeddings or len(result.embeddings) == 0:
        raise HTTPException(status_code=500, detail="Embedding returned no result")
    vals = list(result.embeddings[0].values)
    return normalize_embedding(vals)
