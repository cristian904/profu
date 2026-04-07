"""
Integration tests for solve-problem SSE endpoints.
"""

import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient

from ai_backend.main import app
from ai_backend.config import settings

client = TestClient(app)


class TestSolveProblemQuotaStream:
    """Test quota exceeded streaming response format."""

    @patch("ai_backend.common.supabase_helpers.is_solve_quota_exceeded")
    def test_quota_limit_stream_includes_done(self, mock_quota_exceeded: object) -> None:
        """When quota is exceeded, stream should still end with [DONE]."""
        settings.solve_monthly_quota_threshold = 1
        mock_quota_exceeded.return_value = True

        response = client.post(
            "/solve-problem/stream",
            json={
                "query": "Test",
                "problem_text": "x+1=2",
                "history": [],
            },
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        assert "data: [DONE]" in response.text


class TestSuggestProblemAuth:
    """Suggest-problem requires JWT."""

    @pytest.mark.no_auth_dependency_override
    def test_suggest_problem_401_without_auth(self) -> None:
        """Unauthenticated requests must be rejected."""
        response = client.post(
            "/rag/suggest-problem",
            json={"problem_text": "x + 1 = 2"},
        )
        # 401 when JWT secret is configured; 503 when auth is not configured in the environment
        assert response.status_code in (401, 503)

