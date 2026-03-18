"""
Integration tests for solve-problem SSE endpoints.
"""

import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from ai_backend.main import app
from ai_backend.routers.common import get_current_user_id
from ai_backend.config import settings

client = TestClient(app)


class TestSolveProblemQuotaStream:
    """Test quota exceeded streaming response format."""

    @patch("ai_backend.routers.solve_problem.get_solve_quota_count")
    def test_quota_limit_stream_includes_done(self, mock_get_count):
        """When quota is exceeded, stream should still end with [DONE]."""
        settings.solve_monthly_quota_threshold = 1
        mock_get_count.return_value = 2

        app.dependency_overrides[get_current_user_id] = lambda: uuid.UUID("00000000-0000-0000-0000-000000000000")
        try:
            response = client.post(
                "/solve-problem/stream",
                json={
                    "query": "Test",
                    "problem_text": "x+1=2",
                    "history": [],
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        assert "data: [DONE]" in response.text

