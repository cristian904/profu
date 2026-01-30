"""
Integration tests for the streaming functionality.
Tests both Clarify Once and Clarify Step-by-Step streaming endpoints.
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from ai_backend.main import app

client = TestClient(app)


class TestStreamingIntegration:
    """Integration tests for SSE streaming (Clarify Once mode)."""
    
    @patch('ai_backend.routers.clarify_once.get_llm')
    def test_stream_response_format(self, mock_get_llm):
        """Test that streaming response follows SSE format."""
        # Mock LLM to return test chunks
        mock_chunk = AsyncMock()
        mock_chunk.content = "Test response"
        
        mock_llm = AsyncMock()
        mock_llm.astream = AsyncMock(return_value=iter([mock_chunk]))
        mock_get_llm.return_value = mock_llm
        
        response = client.post(
            "/clarify/once-stream",
            json={"query": "Test"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert "cache-control" in response.headers
        assert response.headers["cache-control"] == "no-cache"
    
    @patch('ai_backend.routers.clarify_once.get_llm')
    def test_stream_includes_done_signal(self, mock_get_llm):
        """Test that streaming includes [DONE] signal."""
        mock_chunk = AsyncMock()
        mock_chunk.content = "Response"
        
        mock_llm = AsyncMock()
        mock_llm.astream = AsyncMock(return_value=iter([mock_chunk]))
        mock_get_llm.return_value = mock_llm
        
        response = client.post(
            "/clarify/once-stream",
            json={"query": "Test"}
        )
        
        content = response.text
        assert "data: [DONE]" in content
    
    @patch('ai_backend.routers.clarify_once.get_llm')
    def test_stream_handles_empty_chunks(self, mock_get_llm):
        """Test that streaming handles empty chunks gracefully."""
        mock_chunk_empty = AsyncMock()
        mock_chunk_empty.content = ""
        mock_chunk_valid = AsyncMock()
        mock_chunk_valid.content = "Valid"
        
        mock_llm = AsyncMock()
        mock_llm.astream = AsyncMock(return_value=iter([mock_chunk_empty, mock_chunk_valid]))
        mock_get_llm.return_value = mock_llm
        
        response = client.post(
            "/clarify/once-stream",
            json={"query": "Test"}
        )
        
        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling in streaming."""
    
    @patch('ai_backend.routers.clarify_once.get_llm')
    def test_stream_handles_llm_errors(self, mock_get_llm):
        """Test that streaming handles LLM errors gracefully."""
        mock_llm = AsyncMock()
        mock_llm.astream.side_effect = Exception("LLM Error")
        mock_get_llm.return_value = mock_llm
        
        response = client.post(
            "/clarify/once-stream",
            json={"query": "Test"}
        )
        
        # Should still return 200 but with error in stream
        assert response.status_code == 200
        content = response.text
        assert "Eroare:" in content or "data: [DONE]" in content
