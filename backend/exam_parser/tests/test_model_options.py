"""
Unit tests for exam_parser.pipeline.model_options (LLM preset helpers).
"""

from __future__ import annotations

from exam_parser.pipeline import model_options


def test_api_ids_for_argparse_order_matches_choices() -> None:
    """``api_ids_for_argparse`` preserves order from ``LLM_MODEL_CHOICES``."""
    ids = model_options.api_ids_for_argparse()
    assert ids == [pair[1] for pair in model_options.LLM_MODEL_CHOICES]


def test_label_for_api_id_known() -> None:
    """Known API id resolves to its display label."""
    mid = model_options.DEFAULT_LLM_MODEL_ID
    lbl = model_options.label_for_api_id(mid)
    assert lbl == "Gemini 2.5 Flash Lite (default)"


def test_label_for_api_id_unknown_returns_raw() -> None:
    """Unknown API id is returned unchanged."""
    assert model_options.label_for_api_id("unknown-model-id") == "unknown-model-id"


def test_default_llm_model_index_points_at_flash_lite() -> None:
    """Default index matches Flash Lite entry in argparse choices."""
    idx = model_options.default_llm_model_index()
    assert model_options.api_ids_for_argparse()[idx] == model_options.DEFAULT_LLM_MODEL_ID


def test_default_llm_model_id_is_flash_lite() -> None:
    """Default constant matches third preset (Flash Lite)."""
    assert model_options.DEFAULT_LLM_MODEL_ID == "gemini-2.5-flash-lite"
