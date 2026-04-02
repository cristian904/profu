"""
Exam simulation timestamps for Postgres (Europe/Bucharest wall clock).
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

_RO_TZ = ZoneInfo("Europe/Bucharest")


def format_exam_timestamp_for_db(moment: datetime | None = None) -> str:
    """
    Build the string written to ``exam_simulations.started_at`` / ``finished_at``.

    Args:
        moment: Instant to format; defaults to "now" in Europe/Bucharest.

    Returns:
        Timestamp like ``2026-03-21 11:07:18``.
    """
    if moment is None:
        aware = datetime.now(_RO_TZ)
    else:
        if moment.tzinfo is None:
            aware = moment.replace(tzinfo=_RO_TZ)
        else:
            aware = moment.astimezone(_RO_TZ)
    return aware.strftime("%Y-%m-%d %H:%M:%S")
