"""
Parse clarify streaming SSE bodies produced by ai_backend (escape_sse_data + sse_data_line).
"""

from __future__ import annotations


def unescape_sse_payload(payload: str) -> str:
    """
    Reverse escape_sse_data: literal backslash-n sequences become newlines.

    Args:
        payload: Single SSE data payload (without the ``data: `` prefix).

    Returns:
        Unescaped text for UI/aggregation.
    """
    if not payload:
        return ""
    return payload.replace("\\n", "\n")


def parse_clarify_sse_to_assistant_text(sse_text: str) -> str:
    """
    Accumulate assistant-visible content from a full SSE HTTP response body.

    Skips control lines: ``[DONE]``, ``[META]...``, ``[THINKING]``.

    Args:
        sse_text: Raw response text (e.g. from ``httpx`` after stream read).

    Returns:
        Concatenated assistant message text for one request/response cycle.
    """
    if not sse_text:
        return ""
    parts: list[str] = []
    for raw_line in sse_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("data: "):
            continue
        payload = line[6:].strip()
        if payload == "[DONE]":
            break
        if payload == "[THINKING]":
            continue
        if payload.startswith("[META]"):
            continue
        parts.append(unescape_sse_payload(payload))
    return "".join(parts)
