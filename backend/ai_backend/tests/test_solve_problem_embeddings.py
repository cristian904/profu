"""
Unit tests for solve_problem embeddings helpers.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from ai_backend.config import settings
from ai_backend.services.solve_problem.embeddings import embed_query, normalize_embedding


class TestNormalizeEmbedding:
    """Tests for normalize_embedding."""

    def test_unit_vector_unchanged(self) -> None:
        out = normalize_embedding([1.0, 0.0, 0.0])
        assert out == [1.0, 0.0, 0.0]

    def test_typical_vector(self) -> None:
        out = normalize_embedding([3.0, 4.0])
        assert abs(out[0] - 0.6) < 1e-9
        assert abs(out[1] - 0.8) < 1e-9

    def test_zero_norm_returns_original(self) -> None:
        zeros = [0.0, 0.0, 0.0]
        assert normalize_embedding(zeros) is zeros or normalize_embedding(zeros) == zeros


class TestEmbedQuery:
    """Tests for embed_query with mocked Gemini client."""

    @patch.object(settings, "google_api_key", "")
    def test_missing_api_key(self) -> None:
        with pytest.raises(HTTPException) as exc:
            embed_query("hello")
        assert exc.value.status_code == 500

    @patch.object(settings, "google_api_key", "fake-key")
    @patch("google.genai.Client")
    def test_success_returns_normalized(self, mock_client_cls: MagicMock) -> None:
        embedding_vals = [3.0, 4.0, 0.0]
        emb_obj = MagicMock()
        emb_obj.values = embedding_vals
        result_mock = MagicMock()
        result_mock.embeddings = [emb_obj]
        client = MagicMock()
        client.models.embed_content.return_value = result_mock
        mock_client_cls.return_value = client

        out = embed_query("query text")
        mock_client_cls.assert_called_once_with(api_key="fake-key")
        norm = normalize_embedding(embedding_vals)
        assert len(out) == len(norm)
        assert abs(out[0] - norm[0]) < 1e-9

    @patch.object(settings, "google_api_key", "fake-key")
    @patch("google.genai.Client")
    def test_empty_embeddings_raises(self, mock_client_cls: MagicMock) -> None:
        result_mock = MagicMock()
        result_mock.embeddings = []
        client = MagicMock()
        client.models.embed_content.return_value = result_mock
        mock_client_cls.return_value = client

        with pytest.raises(HTTPException) as exc:
            embed_query("x")
        assert exc.value.status_code == 500
