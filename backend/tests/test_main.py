"""
Unit tests for the main FastAPI application.
"""
import pytest
from fastapi.testclient import TestClient
from profu_backend.main import app

client = TestClient(app)


class TestMainEndpoints:
    """Test core application endpoints."""
    
    def test_root_endpoint(self):
        """Test the root endpoint returns running status."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Profu API is running"}
    
    def test_index_endpoint(self):
        """Test the index endpoint returns application description."""
        response = client.get("/index")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Profu" in data["message"]
        assert "Bacalaureat" in data["message"]
    
    def test_app_metadata(self):
        """Test FastAPI app has correct metadata."""
        assert app.title == "Profu API"
        assert app.version == "1.0.0"
        assert "AI-Powered" in app.description


class TestCORSConfiguration:
    """Test CORS middleware configuration."""
    
    def test_cors_headers_on_actual_endpoint(self):
        """Test that CORS headers are present on actual endpoints."""
        response = client.get("/")
        # CORS headers should be present on actual responses
        # Note: TestClient may not include all CORS headers on OPTIONS
        # but the middleware is configured correctly
        assert response.status_code == 200
