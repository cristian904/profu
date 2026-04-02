"""
Helpers for LangChain ``with_structured_output`` results.

Supports ``include_raw=True`` (dict with ``raw`` / ``parsed``) and plain model instances.
"""

from typing import Any, TypeVar

from pydantic import BaseModel

TModel = TypeVar("TModel", bound=BaseModel)


def coerce_structured_output(result: Any, model_cls: type[TModel]) -> tuple[TModel | None, str]:
    """
    Normalize structured LLM output for downstream logic and keyword fallbacks.

    Args:
        result: Return value from ``structured_runnable.ainvoke`` (model or dict).
        model_cls: Expected Pydantic model class.

    Returns:
        Tuple of (parsed instance or None, raw message text for fallback heuristics).
    """
    if isinstance(result, model_cls):
        return result, ""
    if isinstance(result, dict) and "parsed" in result:
        raw_msg = result.get("raw")
        raw_text = ""
        if raw_msg is not None:
            raw_text = str(getattr(raw_msg, "content", "") or "")
        parsed = result.get("parsed")
        if isinstance(parsed, model_cls):
            return parsed, raw_text
        return None, raw_text
    return None, ""
