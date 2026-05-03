"""Ollama model id for the exam parser pipeline (UI + CLI)."""
from __future__ import annotations

# Single supported model for markdown → JSON (UI + defaults).
OLLAMA_MODEL_CHOICES: list[tuple[str, str]] = [
    ("Qwen 2.5 Coder 7B", "qwen2.5-coder:7b"),
]

DEFAULT_OLLAMA_MODEL_ID: str = OLLAMA_MODEL_CHOICES[0][1]


def ollama_ids_for_argparse() -> list[str]:
    """Ollama model ids for argparse ``choices``."""
    return [pair[1] for pair in OLLAMA_MODEL_CHOICES]


def label_for_ollama_id(ollama_id: str) -> str:
    """Human-readable label for an Ollama model id, or the raw id if unknown."""
    for lbl, mid in OLLAMA_MODEL_CHOICES:
        if mid == ollama_id:
            return lbl
    return ollama_id


def default_ollama_model_index() -> int:
    """Index of the default Ollama model (always 0 while only one choice exists)."""
    return 0
