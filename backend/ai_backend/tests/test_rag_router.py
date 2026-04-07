"""
Router tests for RAG suggest-problem (quota, validation, vector path).
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from ai_backend.common import get_supabase_client
from ai_backend.config import settings
from ai_backend.main import app

client = TestClient(app)


class TestRagSuggestProblemRouter:
    """Tests for /rag/suggest-problem."""

    def test_empty_problem_text_400(self) -> None:
        response = client.post(
            "/rag/suggest-problem",
            json={"problem_text": "   "},
        )
        assert response.status_code == 400

    @patch("ai_backend.routers.rag.is_solve_quota_exceeded", return_value=True)
    def test_suggest_quota_403(self, _mock_q: MagicMock) -> None:
        response = client.post(
            "/rag/suggest-problem",
            json={"problem_text": "x + 1"},
        )
        assert response.status_code == 403

    @patch("ai_backend.routers.rag.is_solve_quota_exceeded", return_value=False)
    @patch("ai_backend.services.rag.suggest_similar.embed_query")
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
                "/rag/suggest-problem",
                json={"problem_text": "integral"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "problems" in data
            assert len(data["problems"]) == 2
        finally:
            app.dependency_overrides.pop(get_supabase_client, None)
            settings.solve_monthly_quota_threshold = prev

    @patch("ai_backend.routers.rag.is_solve_quota_exceeded", return_value=False)
    def test_suggest_supabase_unconfigured_500(self, _mock_quota: MagicMock) -> None:
        """When Supabase client dependency is None, suggest should fail clearly."""
        app.dependency_overrides[get_supabase_client] = lambda: None
        try:
            response = client.post(
                "/rag/suggest-problem",
                json={"problem_text": "linear algebra"},
            )
            assert response.status_code == 500
            assert "SUPABASE" in response.json().get("detail", "")
        finally:
            app.dependency_overrides.pop(get_supabase_client, None)

    @patch("ai_backend.routers.rag.is_solve_quota_exceeded", return_value=False)
    @patch("ai_backend.services.rag.suggest_similar.embed_query")
    def test_suggest_embedding_failure_500(
        self,
        mock_embed: MagicMock,
        _mock_quota: MagicMock,
    ) -> None:
        """Non-HTTP errors from embedding should become 500."""
        mock_embed.side_effect = RuntimeError("embed down")
        sb = MagicMock()
        app.dependency_overrides[get_supabase_client] = lambda: sb
        try:
            response = client.post(
                "/rag/suggest-problem",
                json={"problem_text": "x"},
            )
            assert response.status_code == 500
        finally:
            app.dependency_overrides.pop(get_supabase_client, None)

    @patch("ai_backend.routers.rag.is_solve_quota_exceeded", return_value=False)
    @patch("ai_backend.services.rag.suggest_similar.embed_query", return_value=[0.1] * 8)
    def test_suggest_rpc_failure_500(
        self,
        _mock_embed: MagicMock,
        _mock_quota: MagicMock,
    ) -> None:
        """RPC errors from match_documents should map to 500."""
        rpc = MagicMock()
        rpc.execute.side_effect = RuntimeError("rpc fail")
        sb = MagicMock()
        sb.rpc.return_value = rpc
        app.dependency_overrides[get_supabase_client] = lambda: sb
        try:
            response = client.post(
                "/rag/suggest-problem",
                json={"problem_text": "integral"},
            )
            assert response.status_code == 500
        finally:
            app.dependency_overrides.pop(get_supabase_client, None)

    @patch("ai_backend.routers.rag.is_solve_quota_exceeded", return_value=False)
    @patch("ai_backend.services.rag.suggest_similar.embed_query", return_value=[0.1] * 8)
    def test_suggest_empty_results_message(
        self,
        _mock_embed: MagicMock,
        _mock_quota: MagicMock,
    ) -> None:
        """Empty vector hits should return the Romanian empty message."""
        rpc = MagicMock()
        rpc.execute.return_value = MagicMock(data=[])
        sb = MagicMock()
        sb.rpc.return_value = rpc
        app.dependency_overrides[get_supabase_client] = lambda: sb
        try:
            response = client.post(
                "/rag/suggest-problem",
                json={"problem_text": "rare topic"},
            )
            assert response.status_code == 200
            body = response.json()
            assert "Nu am găsit" in body["message"]
            assert body["problems"] == []
        finally:
            app.dependency_overrides.pop(get_supabase_client, None)
