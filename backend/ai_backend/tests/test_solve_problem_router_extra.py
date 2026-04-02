"""
Extra router tests for solve-problem (validation, quota, suggest).
"""

import io
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from ai_backend.common import get_supabase_client
from ai_backend.config import settings
from ai_backend.main import app

client = TestClient(app)


class TestSolveProblemUploadValidation:
    """Tests for /solve-problem/upload validation paths."""

    @patch("ai_backend.routers.solve_problem.is_solve_quota_exceeded", return_value=False)
    def test_empty_file_400(self, _mock_quota: MagicMock) -> None:
        files = {"file": ("empty.png", io.BytesIO(b""), "image/png")}
        response = client.post("/solve-problem/upload", files=files)
        assert response.status_code == 400

    @patch("ai_backend.routers.solve_problem.is_solve_quota_exceeded", return_value=False)
    def test_invalid_not_image_400(self, _mock_quota: MagicMock) -> None:
        files = {"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")}
        response = client.post("/solve-problem/upload", files=files)
        assert response.status_code == 400

    @patch("ai_backend.routers.solve_problem.is_solve_quota_exceeded", return_value=True)
    def test_quota_403_on_upload(self, _mock_quota: MagicMock) -> None:
        files = {"file": ("x.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")}
        response = client.post("/solve-problem/upload", files=files)
        assert response.status_code == 403


class TestSuggestProblemRouter:
    """Tests for /solve-problem/suggest-problem."""

    def test_empty_problem_text_400(self) -> None:
        response = client.post(
            "/solve-problem/suggest-problem",
            json={"problem_text": "   "},
        )
        assert response.status_code == 400

    @patch("ai_backend.routers.solve_problem.is_solve_quota_exceeded", return_value=True)
    def test_suggest_quota_403(self, _mock_q: MagicMock) -> None:
        response = client.post(
            "/solve-problem/suggest-problem",
            json={"problem_text": "x + 1"},
        )
        assert response.status_code == 403

    @patch("ai_backend.routers.solve_problem.is_solve_quota_exceeded", return_value=False)
    @patch("ai_backend.routers.solve_problem._embed_query")
    def test_suggest_success_mocked(
        self,
        mock_embed: MagicMock,
        _mock_quota: MagicMock,
    ) -> None:
        mock_embed.return_value = [0.1] * 8
        rpc = MagicMock()
        rpc.execute.return_value = MagicMock(
            data=[{"id": 1, "content": "Problem A"}, {"id": 2, "content": "Problem B"}]
        )
        sb = MagicMock()
        sb.rpc.return_value = rpc

        prev = settings.solve_monthly_quota_threshold
        settings.solve_monthly_quota_threshold = 0
        app.dependency_overrides[get_supabase_client] = lambda: sb
        try:
            response = client.post(
                "/solve-problem/suggest-problem",
                json={"problem_text": "integral"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "problems" in data
            assert len(data["problems"]) == 2
        finally:
            app.dependency_overrides.pop(get_supabase_client, None)
            settings.solve_monthly_quota_threshold = prev
