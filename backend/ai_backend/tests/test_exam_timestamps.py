"""
Tests for exam timestamp formatting written to exam_simulations.
"""

import re
from datetime import datetime

from zoneinfo import ZoneInfo

from ai_backend.utils.exam_timestamps import format_exam_timestamp_for_db


def test_format_exam_timestamp_matches_expected_pattern() -> None:
    """
    Output must look like 2026-03-21 11:07:18 (no T, no timezone suffix).
    """
    s = format_exam_timestamp_for_db()
    assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", s), s


def test_format_exam_timestamp_fixed_moment() -> None:
    """
    Known instant is formatted in Europe/Bucharest.
    """
    utc = datetime(2026, 3, 21, 9, 7, 18, tzinfo=ZoneInfo("UTC"))
    s = format_exam_timestamp_for_db(utc)
    # 09:07 UTC -> 11:07 EET (March is DST boundary; 21 Mar 2026 Romania is EET UTC+2)
    assert s == "2026-03-21 11:07:18"
