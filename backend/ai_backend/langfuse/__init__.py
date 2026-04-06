"""
Langfuse integration module for AI backend tracing, monitoring, and prompt management.

Provides client initialization, trace context management,
LangChain callback handler wiring, and ``PromptComposer``
so every AI interaction is observable in the Langfuse dashboard
and prompts are version-controlled via Langfuse Prompt Management.
"""

from ai_backend.langfuse.client import create_langfuse_client, get_langfuse_client
from ai_backend.langfuse.context import langfuse_trace_context, llm_config, node_span, resolve_session_id
from ai_backend.langfuse.prompts import (
    PromptComposer,
    create_prompt_composer,
    get_prompt_composer,
)

__all__ = [
    "create_langfuse_client",
    "get_langfuse_client",
    "langfuse_trace_context",
    "llm_config",
    "node_span",
    "resolve_session_id",
    "PromptComposer",
    "create_prompt_composer",
    "get_prompt_composer",
]
