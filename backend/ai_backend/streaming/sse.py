"""
Server-Sent Events (SSE) formatting helpers.

Routers use these helpers to keep the streaming wire format consistent.
"""

import json
import time


def escape_sse_data(text: str) -> str:
    """
    Escape newline characters for SSE payloads.

    The frontend expects literal \"\\\\n\" sequences in the `data:` payload.

    Args:
        text: Raw content to send over SSE.

    Returns:
        Content with newlines replaced by the literal sequence \"\\\\n\".
    """
    if not isinstance(text, str):
        return ""
    return text.replace("\n", "\\n")


def sse_data_line(data: str) -> str:
    """
    Format a single SSE `data:` line with a blank line terminator.

    Args:
        data: The raw data string (already escaped if needed).

    Returns:
        SSE formatted message: \"data: {data}\\n\\n\".
    """
    return f"data: {data}\n\n"


def emit_done() -> str:
    """
    Emit the standard stream completion marker.

    Returns:
        SSE line for [DONE].
    """
    return sse_data_line("[DONE]")


def emit_thinking() -> str:
    """
    Emit the standard thinking marker used by the frontend.

    Returns:
        SSE line for [THINKING].
    """
    return sse_data_line("[THINKING]")


def emit_meta_ttft(start_time: float) -> str:
    """
    Emit stream metadata with TTFT (time-to-first-token).

    Args:
        start_time: `time.time()` value recorded before streaming begins.

    Returns:
        SSE line: data: [META]{\"ttft\": <seconds>}\\n\\n
    """
    ttft = max(0.0, time.time() - float(start_time))
    payload = json.dumps({"ttft": round(ttft, 3)})
    return sse_data_line(f"[META]{payload}")

