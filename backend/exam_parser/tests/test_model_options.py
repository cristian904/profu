"""
Unit tests for exam_parser.pipeline.model_options (Ollama model id).
"""

from __future__ import annotations

from exam_parser.pipeline import model_options


def test_ollama_ids_for_argparse_order_matches_choices() -> None:
    """``ollama_ids_for_argparse`` matches ``OLLAMA_MODEL_CHOICES``."""
    ids = model_options.ollama_ids_for_argparse()
    assert ids == [pair[1] for pair in model_options.OLLAMA_MODEL_CHOICES]


def test_label_for_ollama_id_known() -> None:
    """Known Ollama id resolves to its display label."""
    mid = model_options.DEFAULT_OLLAMA_MODEL_ID
    lbl = model_options.label_for_ollama_id(mid)
    assert lbl == "Qwen 2.5 Coder 7B"


def test_label_for_ollama_id_unknown_returns_raw() -> None:
    """Unknown Ollama id is returned unchanged."""
    assert model_options.label_for_ollama_id("unknown-model-id") == "unknown-model-id"


def test_default_ollama_model_index_is_zero() -> None:
    """Single-choice list: default index is 0."""
    idx = model_options.default_ollama_model_index()
    assert idx == 0
    assert model_options.ollama_ids_for_argparse()[idx] == model_options.DEFAULT_OLLAMA_MODEL_ID


def test_default_ollama_model_id_is_qwen25_coder_7b() -> None:
    """Pinned UI/CLI model."""
    assert model_options.DEFAULT_OLLAMA_MODEL_ID == "qwen2.5-coder:7b"
