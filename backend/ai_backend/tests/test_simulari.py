"""
Tests for the Simulari feature and router.
"""

import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from ai_backend.main import app
from ai_backend.routers import simulari


client = TestClient(app)


class TestSimulariGenerate:
    """
    Tests for the /simulari/generate endpoint.
    """

    @patch("ai_backend.routers.simulari.get_user_id_from_request")
    @patch("ai_backend.routers.simulari._get_simulation_service")
    def test_generate_simulation_success(self, mock_get_service, mock_get_user_id):
        """
        Positive: simulation is created successfully and returns an id.
        """
        fake_user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
        mock_get_user_id.return_value = fake_user_id
        service_mock = MagicMock()
        service_mock.create_simulation.return_value = 123
        mock_get_service.return_value = service_mock

        response = client.post(
            "/simulari/generate",
            json={"school_subject": "math"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["simulation_id"] == 123
        assert data["school_subject"] == "math"

    @patch("ai_backend.routers.simulari.get_user_id_from_request")
    @patch("ai_backend.routers.simulari._get_simulation_service")
    def test_generate_simulation_conflict_when_no_problems(self, mock_get_service, mock_get_user_id):
        """
        Negative: when there are no exam_problems, endpoint should return 409.
        """
        fake_user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
        mock_get_user_id.return_value = fake_user_id
        service_mock = MagicMock()
        service_mock.create_simulation.side_effect = ValueError("No exam problem available")
        mock_get_service.return_value = service_mock

        response = client.post(
            "/simulari/generate",
            json={"school_subject": "math"},
        )

        assert response.status_code == 409


class TestSimulariScoring:
    """
    Tests for the /simulari/scoring endpoint.
    """

    @patch("ai_backend.routers.simulari.get_user_id_from_request")
    def test_scoring_success(self, mock_get_user_id):
        """
        Positive: scoring updates per-problem and persists total score.
        """
        fake_user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
        mock_get_user_id.return_value = fake_user_id

        supabase_mock = MagicMock()
        app.dependency_overrides[simulari.get_supabase_client] = lambda: supabase_mock

        # Simulation belongs to user
        supabase_mock.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": 10, "auth_user_id": str(fake_user_id)}
        ]

        # Updating problem scores returns non-empty data
        supabase_mock.table.return_value.update.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": 1}
        ]

        response = client.post(
            "/simulari/scoring",
            json={
                "simulation_id": 10,
                "problems": [
                    {"subject_number": 1, "problem_number": 1, "student_score": 5},
                    {"subject_number": 2, "problem_number": 1, "student_score": 15},
                ],
            },
        )

        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["simulation_id"] == 10
        assert data["total_score"] == 20

    @patch("ai_backend.routers.simulari.get_user_id_from_request")
    def test_scoring_forbidden_for_other_user(self, mock_get_user_id):
        """
        Negative: scoring another user's simulation returns 403.
        """
        fake_user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
        mock_get_user_id.return_value = fake_user_id

        supabase_mock = MagicMock()
        app.dependency_overrides[simulari.get_supabase_client] = lambda: supabase_mock

        # Simulation belongs to a different user
        supabase_mock.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": 10, "auth_user_id": str(uuid.uuid4())}
        ]

        response = client.post(
            "/simulari/scoring",
            json={
                "simulation_id": 10,
                "problems": [
                    {"subject_number": 1, "problem_number": 1, "student_score": 5},
                ],
            },
        )

        app.dependency_overrides.clear()

        assert response.status_code == 403

