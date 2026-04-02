"""
Unit tests for simulation feature helpers (school_subject DB aliases).
"""

from ai_backend.services.simulari.service import _school_subject_db_values


class TestSchoolSubjectDbValues:
    """Tests for _school_subject_db_values mapping."""

    def test_math_includes_mate(self) -> None:
        """
        Positive: \"math\" should also query \"mate\" rows (merged JSON catalog).
        """
        values = _school_subject_db_values("math")
        assert "math" in values
        assert "mate" in values
        assert len(values) == 2

    def test_mate_includes_math(self) -> None:
        """
        Positive: \"mate\" should also accept \"math\" alias for the same filter set.
        """
        values = _school_subject_db_values("mate")
        assert "mate" in values
        assert "math" in values
