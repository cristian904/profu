"""
Format conversation snippets for guardrails context (no PII expansion beyond provided messages).
"""

from ai_backend.common.models import Message


def format_messages_for_guardrails_context(
    history: list[Message],
    *,
    max_messages: int = 6,
) -> str:
    """
    Build a compact transcript string from recent chat messages for guardrails.

    Args:
        history: Ordered conversation messages from the client or store.
        max_messages: Maximum number of recent messages to include.

    Returns:
        Newline-separated role/content lines, or an empty string when there is no usable history.
    """
    if not history:
        return ""
    tail = history[-max_messages:] if len(history) > max_messages else history
    lines: list[str] = []
    for msg in tail:
        content = (msg.content or "").strip()
        if not content:
            continue
        role = (msg.role or "user").strip().lower()
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
