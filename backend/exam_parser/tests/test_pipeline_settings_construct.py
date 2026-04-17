"""
Construct ``PipelineSettings`` without loading repo ``.env`` (field defaults only).
"""

from __future__ import annotations

from exam_parser.pipeline.settings import PipelineSettings


def test_pipeline_settings_default_model_ids() -> None:
    """Default Ollama and embedding model ids match pipeline expectations."""
    s = PipelineSettings.model_construct(
        google_api_key="test-key",
        supabase_url="http://localhost",
    )
    assert s.ollama_model == "llama3.1:8b"
    assert s.ollama_base_url == "http://127.0.0.1:11434"
    assert s.model_embed == "gemini-embedding-001"
    assert s.nougat_model_id == "facebook/nougat-small"
    assert s.nougat_device == "auto"
    assert s.supabase_service_role_key is None
    assert s.supabase_anon_key is None
