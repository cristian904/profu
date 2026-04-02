"""
Gemini / LangChain chat model factory for dependency injection.
"""

from langchain_google_genai import ChatGoogleGenerativeAI

from ai_backend.common.protocols import LangGraphChatModel
from ai_backend.config import settings


def get_llm() -> LangGraphChatModel:
    """
    Initialize and return Gemini LLM instance (model from config).

    Use with FastAPI ``Depends(get_llm)`` for dependency injection.
    """
    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=0.0,
        google_api_key=settings.google_api_key,
    )
