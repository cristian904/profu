"""
Unit tests for the clarify routers (explica and guided_learning).
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from ai_backend.config import settings
from ai_backend.main import app
from ai_backend.common.llm import get_llm
from ai_backend.common.models import Message, QueryRequest

client = TestClient(app)


class TestClarifyModels:
    """Test Pydantic models for clarify router."""
    
    def test_message_model(self):
        """Test Message model validation."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
    
    def test_query_request_without_history(self):
        """Test QueryRequest with empty history."""
        req = QueryRequest(query="What is a derivative?")
        assert req.query == "What is a derivative?"
        assert req.history == []
    
    def test_query_request_with_history(self):
        """Test QueryRequest with conversation history."""
        history = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!")
        ]
        req = QueryRequest(query="Follow-up question", history=history)
        assert req.query == "Follow-up question"
        assert len(req.history) == 2
        assert req.history[0].role == "user"


class TestClarifyOnceEndpoint:
    """Test the /clarify/once-stream endpoint (Clarify Once mode)."""

    def test_clarify_once_stream_endpoint_exists(self) -> None:
        """Test that the /clarify/once-stream endpoint exists and accepts POST."""
        response = client.post(
            "/clarify/once-stream",
            json={"query": "Test question"},
        )
        
        # Should return 200 and be a streaming response
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
    
    def test_clarify_once_stream_requires_query(self):
        """Test that the endpoint requires a query parameter."""
        response = client.post("/clarify/once-stream", json={})
        assert response.status_code == 422  # Validation error
    
    def test_clarify_once_stream_with_history(self) -> None:
        """Test streaming with conversation history."""
        response = client.post(
            "/clarify/once-stream",
            json={
                "query": "Can you explain more?",
                "history": [
                    {"role": "user", "content": "What is calculus?"},
                    {"role": "assistant", "content": "Calculus is..."}
                ]
            }
        )
        
        assert response.status_code == 200


class TestClarifyStepByStepEndpoint:
    """Test the /clarify/step-by-step-stream endpoint (Step-by-step mode)."""

    def test_step_by_step_stream_endpoint_exists(self) -> None:
        """Test that the /clarify/step-by-step-stream endpoint exists and accepts POST."""
        response = client.post(
            "/clarify/step-by-step-stream",
            json={"query": "Test question"}
        )
        
        # Should return 200 and be a streaming response
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
    
    def test_step_by_step_stream_requires_query(self):
        """Test that the endpoint requires a query parameter."""
        response = client.post("/clarify/step-by-step-stream", json={})
        assert response.status_code == 422  # Validation error
    
    def test_step_by_step_stream_with_history(self) -> None:
        """Test streaming with conversation history (follow-up queries)."""
        response = client.post(
            "/clarify/step-by-step-stream",
            json={
                "query": "Can you explain more?",
                "history": [
                    {"role": "user", "content": "What is calculus?"},
                    {"role": "assistant", "content": "Calculus is..."}
                ]
            }
        )
        
        assert response.status_code == 200


class TestLLMIntegration:
    """Test LLM initialization and configuration."""

    @pytest.mark.no_llm_dependency_override
    @patch.object(settings, "google_api_key", "test_key")
    def test_get_llm_with_api_key(self):
        """Test LLM initialization with API key."""
        llm = get_llm()
        assert llm is not None
        assert llm.model == settings.gemini_model
        assert llm.temperature == 0.0

    @pytest.mark.no_llm_dependency_override
    @patch.object(settings, "google_api_key", "")
    def test_get_llm_without_api_key(self):
        """Test that get_llm raises error without API key."""
        with pytest.raises(ValueError, match="GOOGLE_API_KEY not found"):
            get_llm()


class TestPromptsConfiguration:
    """Test prompts loading from YAML."""
    
    def test_prompts_loaded(self):
        """Test that prompts are loaded from YAML file."""
        from ai_backend.common.prompts import PROMPTS
        
        assert PROMPTS is not None
        assert 'clarify_chat' in PROMPTS
        assert 'system_prompt' in PROMPTS['clarify_chat']
        assert 'guided_learning' in PROMPTS
    
    def test_clarify_system_prompt_content(self):
        """Test that clarify system prompt contains expected content."""
        from ai_backend.common.prompts import PROMPTS
        
        prompt = PROMPTS['clarify_chat']['system_prompt']
        assert 'profesor' in prompt.lower()
        assert 'markdown' in prompt.lower()
        assert 'latex' in prompt.lower()
        assert 'graph' in prompt.lower()
    
    def test_guided_learning_prompts_exist(self):
        """Test that guided learning prompts are configured."""
        from ai_backend.common.prompts import PROMPTS
        
        assert 'prerequisite_generator' in PROMPTS['guided_learning']
        assert 'question_asker' in PROMPTS['guided_learning']
        assert 'final_explainer' in PROMPTS['guided_learning']
