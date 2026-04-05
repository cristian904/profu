"""
Extra router tests for solve-problem (validation, quota, suggest).
"""

import io
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from ai_backend.common import get_supabase_client
from ai_backend.config import settings
from ai_backend.main import app
from ai_backend.routers.solve_problem import _embed_query, _normalize_embedding

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

    @patch("ai_backend.routers.solve_problem.is_solve_quota_exceeded", return_value=False)
    @patch("ai_backend.routers.solve_problem.perform_ocr", new_callable=AsyncMock)
    def test_upload_success_by_extension_when_content_type_generic(
        self,
        mock_ocr: AsyncMock,
        _mock_quota: MagicMock,
    ) -> None:
        """Accept image by filename when content_type is not image/*."""
        mock_ocr.return_value = "extracted text"
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
        files = {"file": ("exam.PNG", io.BytesIO(png), "application/octet-stream")}
        response = client.post("/solve-problem/upload", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["problem_text"] == "extracted text"

    @patch("ai_backend.routers.solve_problem.is_solve_quota_exceeded", return_value=False)
    @patch("ai_backend.routers.solve_problem.perform_ocr", new_callable=AsyncMock)
    def test_upload_http_exception_reraised(
        self,
        mock_ocr: AsyncMock,
        _mock_quota: MagicMock,
    ) -> None:
        """HTTPException from OCR layer should propagate without wrapping to 500."""
        from fastapi import HTTPException

        mock_ocr.side_effect = HTTPException(status_code=400, detail="bad image")
        files = {"file": ("x.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")}
        response = client.post("/solve-problem/upload", files=files)
        assert response.status_code == 400

    @patch("ai_backend.routers.solve_problem.is_solve_quota_exceeded", return_value=False)
    @patch("ai_backend.routers.solve_problem.perform_ocr", new_callable=AsyncMock)
    def test_upload_generic_exception_returns_500(
        self,
        mock_ocr: AsyncMock,
        _mock_quota: MagicMock,
    ) -> None:
        """Unexpected OCR errors should map to 500."""
        mock_ocr.side_effect = RuntimeError("ocr exploded")
        files = {"file": ("x.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")}
        response = client.post("/solve-problem/upload", files=files)
        assert response.status_code == 500


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

    @patch("ai_backend.routers.solve_problem.is_solve_quota_exceeded", return_value=False)
    def test_suggest_supabase_unconfigured_500(self, _mock_quota: MagicMock) -> None:
        """When Supabase client dependency is None, suggest should fail clearly."""
        app.dependency_overrides[get_supabase_client] = lambda: None
        try:
            response = client.post(
                "/solve-problem/suggest-problem",
                json={"problem_text": "linear algebra"},
            )
            assert response.status_code == 500
            assert "SUPABASE" in response.json().get("detail", "")
        finally:
            app.dependency_overrides.pop(get_supabase_client, None)

    @patch("ai_backend.routers.solve_problem.is_solve_quota_exceeded", return_value=False)
    @patch("ai_backend.routers.solve_problem._embed_query")
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
                "/solve-problem/suggest-problem",
                json={"problem_text": "x"},
            )
            assert response.status_code == 500
        finally:
            app.dependency_overrides.pop(get_supabase_client, None)

    @patch("ai_backend.routers.solve_problem.is_solve_quota_exceeded", return_value=False)
    @patch("ai_backend.routers.solve_problem._embed_query", return_value=[0.1] * 8)
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
                "/solve-problem/suggest-problem",
                json={"problem_text": "integral"},
            )
            assert response.status_code == 500
        finally:
            app.dependency_overrides.pop(get_supabase_client, None)

    @patch("ai_backend.routers.solve_problem.is_solve_quota_exceeded", return_value=False)
    @patch("ai_backend.routers.solve_problem._embed_query", return_value=[0.1] * 8)
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
                "/solve-problem/suggest-problem",
                json={"problem_text": "rare topic"},
            )
            assert response.status_code == 200
            body = response.json()
            assert "Nu am găsit" in body["message"]
            assert body["problems"] == []
        finally:
            app.dependency_overrides.pop(get_supabase_client, None)


class TestSolveProblemEmbeddingWrappers:
    """Thin router wrappers should delegate to service helpers."""

    @patch("ai_backend.routers.solve_problem.normalize_embedding")
    def test_normalize_embedding_wrapper(
        self,
        mock_norm: MagicMock,
    ) -> None:
        mock_norm.return_value = [1.0, 0.0]
        assert _normalize_embedding([3.0, 0.0]) == [1.0, 0.0]
        mock_norm.assert_called_once()

    @patch("ai_backend.routers.solve_problem.embed_query")
    def test_embed_query_wrapper(self, mock_embed: MagicMock) -> None:
        mock_embed.return_value = [0.5]
        assert _embed_query("hi") == [0.5]
        mock_embed.assert_called_once_with("hi")
