"""
Typed state for the clarify-once LangGraph.
"""

from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ClarifyOnceGraphState(TypedDict):
    """State for clarify-once streaming graph."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    request_query: str
    guardrails_context: str
    guardrails_allowed: bool
    guardrails_block_message_ro: str
