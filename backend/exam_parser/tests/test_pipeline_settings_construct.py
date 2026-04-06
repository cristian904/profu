"""
Construct ``PipelineSettings`` without loading repo ``.env`` (field defaults only).
"""

from __future__ import annotations

from exam_parser.pipeline.settings import PipelineSettings


def test_pipeline_settings_default_model_ids() -> None:
    """Default Gemini model ids match pipeline expectations."""
    s = PipelineSettings.model_construct(
        google_api_key="test-key",
        supabase_url="http://localhost",
    )
    assert s.model_vision == "gemini-2.5-flash"
    assert s.model_structured == "gemini-2.5-flash"
    assert s.model_embed == "gemini-embedding-001"
    assert s.supabase_service_role_key is None
    assert s.supabase_anon_key is None
