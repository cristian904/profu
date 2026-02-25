"""
Common utilities and models shared between clarify routers.
"""
from pathlib import Path

import yaml
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from ai_backend.config import settings


# Load prompts from YAML file
prompts_path = Path(__file__).parent.parent / "prompts.yaml"
with open(prompts_path, 'r', encoding='utf-8') as f:
    PROMPTS = yaml.safe_load(f)


def get_llm():
    """Initialize and return Gemini LLM instance (model from config)."""
    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=0.0,
        google_api_key=settings.google_api_key,
    )


class Message(BaseModel):
    """Message model for conversation history"""
    role: str  # "user" or "assistant"
    content: str


class QueryRequest(BaseModel):
    """Request model for chat queries"""
    query: str
    history: list[Message] = []  # Conversation history
