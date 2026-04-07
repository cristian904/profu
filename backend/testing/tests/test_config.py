"""Tests for ``profu_testing.config`` (no secrets in repo)."""

import pytest

from profu_testing.config import ProfuTestingSettings, get_testing_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    """Ensure each test sees fresh env-derived settings."""
    get_testing_settings.cache_clear()
    yield
    get_testing_settings.cache_clear()


def test_resolved_api_base_url_prefers_testing_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """TESTING_API_BASE_URL wins over API_BASE_URL."""
    monkeypatch.setenv("API_BASE_URL", "http://localhost:8080")
    monkeypatch.setenv("TESTING_API_BASE_URL", "http://example.test:9999")
    s = ProfuTestingSettings()
    assert s.resolved_api_base_url == "http://example.test:9999"


def test_resolved_api_base_url_falls_back_to_api_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """API_BASE_URL from root .env is used when testing override is empty."""
    monkeypatch.delenv("TESTING_API_BASE_URL", raising=False)
    monkeypatch.setenv("API_BASE_URL", "http://localhost:8080")
    s = ProfuTestingSettings()
    assert s.resolved_api_base_url == "http://localhost:8080"


def test_checklist_gemini_model_uses_testing_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """TESTING_GEMINI_MODEL overrides GEMINI_MODEL for checklist property."""
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.0-flash")
    monkeypatch.setenv("TESTING_GEMINI_MODEL", "gemini-2.5-flash-lite")
    s = ProfuTestingSettings()
    assert s.checklist_gemini_model == "gemini-2.5-flash-lite"


def test_eval_jwt_strips_bearer_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bearer prefix is removed from eval JWT."""
    monkeypatch.setenv("EVAL_JWT", "Bearer secret-token")
    s = ProfuTestingSettings()
    assert s.eval_jwt == "secret-token"
