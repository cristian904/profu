"""
Extra router tests for solve-problem (validation, quota, upload).
"""

import io
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

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
