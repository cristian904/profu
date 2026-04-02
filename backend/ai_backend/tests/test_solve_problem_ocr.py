"""
Unit tests for solve_problem OCR (mocked vision LLM).
"""

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from PIL import Image

from ai_backend.config import settings
from ai_backend.services.solve_problem.ocr import perform_ocr


def _tiny_png_bytes() -> bytes:
    """Minimal valid PNG for PIL."""
    img = Image.new("RGB", (8, 8), color=(255, 255, 255))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestPerformOcr:
    """Tests for perform_ocr."""

    @patch.object(settings, "google_api_key", "")
    async def test_missing_api_key(self) -> None:
        with pytest.raises(HTTPException) as exc:
            await perform_ocr(_tiny_png_bytes())
        assert exc.value.status_code == 500

    @patch.object(settings, "google_api_key", "k")
    @patch.object(settings, "gemini_model", "gemini-test")
    @patch("langchain_google_genai.ChatGoogleGenerativeAI")
    async def test_pil_path_success(self, mock_llm_cls: MagicMock) -> None:
        llm = MagicMock()
        resp = MagicMock()
        resp.content = "  extracted text  "
        llm.ainvoke = AsyncMock(return_value=resp)
        mock_llm_cls.return_value = llm

        out = await perform_ocr(_tiny_png_bytes())
        assert out == "extracted text"
        mock_llm_cls.assert_called_once()
        llm.ainvoke.assert_awaited_once()

    @patch.object(settings, "google_api_key", "k")
    @patch.object(settings, "gemini_model", "gemini-test")
    @patch("langchain_google_genai.ChatGoogleGenerativeAI")
    async def test_base64_fallback_on_pil_failure(self, mock_llm_cls: MagicMock) -> None:
        llm = MagicMock()
        resp = MagicMock()
        resp.content = "from base64"
        llm.ainvoke = AsyncMock(return_value=resp)
        mock_llm_cls.return_value = llm

        # Corrupt bytes: PIL fails, base64 path still runs with invalid image data
        # Second call succeeds
        corrupt = b"not a real image"
        out = await perform_ocr(corrupt)
        assert out == "from base64"
        assert llm.ainvoke.await_count == 1

    @patch.object(settings, "google_api_key", "k")
    @patch.object(settings, "gemini_model", "gemini-test")
    @patch("langchain_google_genai.ChatGoogleGenerativeAI")
    async def test_both_paths_fail_http_exception(self, mock_llm_cls: MagicMock) -> None:
        llm = MagicMock()
        llm.ainvoke = AsyncMock(side_effect=RuntimeError("api down"))
        mock_llm_cls.return_value = llm

        with pytest.raises(HTTPException) as exc:
            await perform_ocr(b"xxx")
        assert exc.value.status_code == 500
