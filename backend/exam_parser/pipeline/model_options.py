"""Shared Gemini 2.5 model presets for the exam parser pipeline (UI + CLI)."""
from __future__ import annotations

# (display label, API model id)
LLM_MODEL_CHOICES: list[tuple[str, str]] = [
    ("Gemini 2.5 Pro", "gemini-2.5-pro"),
    ("Gemini 2.5 Flash", "gemini-2.5-flash"),
    ("Gemini 2.5 Flash Lite (default)", "gemini-2.5-flash-lite"),
]

DEFAULT_LLM_MODEL_ID: str = LLM_MODEL_CHOICES[2][1]


def api_ids_for_argparse() -> list[str]:
    """Ordered API model ids for argparse ``choices``."""
    return [pair[1] for pair in LLM_MODEL_CHOICES]


def label_for_api_id(api_id: str) -> str:
    """Human-readable label for an API id, or the raw id if unknown."""
    for lbl, mid in LLM_MODEL_CHOICES:
        if mid == api_id:
            return lbl
    return api_id


def default_llm_model_index() -> int:
    """Index of the default (Flash Lite) preset in ``api_ids_for_argparse()``."""
    return api_ids_for_argparse().index(DEFAULT_LLM_MODEL_ID)
