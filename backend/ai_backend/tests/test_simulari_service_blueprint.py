"""
Unit tests for SimulationService internals (mocked Supabase).
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from ai_backend.services.simulari.service import SimulationService, _school_subject_db_values


class TestSchoolSubjectEdgeCases:
    """Extra coverage for _school_subject_db_values."""

    def test_empty_string_returns_empty(self) -> None:
        assert _school_subject_db_values("") == []
        assert _school_subject_db_values("   ") == []

    def test_other_subject_unchanged(self) -> None:
        assert _school_subject_db_values("fizica") == ["fizica"]


class TestSimulationServiceBlueprint:
    """Tests for _fetch_candidates, _choose_one_candidate, create_simulation."""

    def test_fetch_candidates_empty_subject_returns_empty(self) -> None:
        svc = SimulationService(MagicMock())
        with patch(
            "ai_backend.services.simulari.service._school_subject_db_values",
            return_value=[],
        ):
            assert svc._fetch_candidates(" ", 1, 1) == []

    def test_choose_one_candidate_empty_raises(self) -> None:
        svc = SimulationService(MagicMock())
        with pytest.raises(ValueError, match="No exam problem"):
            svc._choose_one_candidate([], 1, 1)

    def test_create_simulation_happy_path(self) -> None:
        client = MagicMock()
        svc = SimulationService(client)

        fake_row = {"id": 42}

        def fetch_side_effect(
            school_subject: str,
            subject_number: int,
            problem_number: int,
        ) -> list:
            return [dict(fake_row, subject_number=subject_number, problem_number=problem_number)]

        with patch.object(svc, "_fetch_candidates", side_effect=fetch_side_effect):
            sim_insert = MagicMock()
            sim_insert.execute.return_value = MagicMock(data=[{"id": 100}])
            prob_insert = MagicMock()
            prob_insert.execute.return_value = MagicMock(data=[{}])

            def table_side_effect(name: str) -> MagicMock:
                t = MagicMock()
                if name == "exam_simulations":
                    t.insert.return_value = sim_insert
                elif name == "exam_simulation_problems":
                    t.insert.return_value = prob_insert
                return t

            client.table.side_effect = table_side_effect

            uid = uuid.uuid4()
            sim_id = svc.create_simulation(auth_user_id=uid, school_subject="mate")
            assert sim_id == 100
            prob_insert.execute.assert_called_once()
