"""
Feature-scoped logging wrapper around `log_json`.

The goal is to keep code readable (single-line log calls) while preserving:
- all JSON attributes produced by `log_json`
- existing `source` values
- traceback behavior (traceback only on level=\"error\")
"""

from __future__ import annotations

import traceback as tb
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from ai_backend.logging.log_utils import log_json


@dataclass(frozen=True)
class FeatureLogger:
    """
    Minimal logger that binds a `source` for all calls.
    """

    source: str

    def info(self, message: str, user_id: Optional[UUID] = None) -> None:
        """
        Log an informational message.
        """
        try:
            log_json(
                source=self.source,
                level="info",
                message=message,
                user_id=user_id,
                traceback=None,
            )
        except Exception:
            # Never let logging break app flow
            return

    def warning(self, message: str, user_id: Optional[UUID] = None) -> None:
        """
        Log a warning message.
        """
        try:
            log_json(
                source=self.source,
                level="warning",
                message=message,
                user_id=user_id,
                traceback=None,
            )
        except Exception:
            return

    def error(
        self,
        error: Exception | str,
        user_id: Optional[UUID] = None,
        traceback: Optional[str] = None,
    ) -> None:
        """
        Log an error.

        Args:
            error: Exception or string message.
            user_id: Optional user id.
            traceback: Optional traceback string. If not provided and `error` is an Exception,
                this method captures the current traceback.
        """
        try:
            message = str(error)
            tb_value = traceback
            if tb_value is None and isinstance(error, Exception):
                tb_value = tb.format_exc()

            log_json(
                source=self.source,
                level="error",
                message=message,
                user_id=user_id,
                traceback=tb_value,
            )
        except Exception:
            return


def get_feature_logger(source: str) -> FeatureLogger:
    """
    Create a feature-scoped logger.

    Args:
        source: Feature name (e.g. \"ocr\", \"solve_problem_stream\").
    """
    return FeatureLogger(source=source)

