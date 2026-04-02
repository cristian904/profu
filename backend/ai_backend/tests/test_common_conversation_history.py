"""Tests for resolve_effective_history."""

import uuid
from unittest.mock import MagicMock, patch

from ai_backend.common.conversation_history import resolve_effective_history
from ai_backend.common.models import Message


class TestResolveEffectiveHistory:
    def test_no_conversation_id_returns_request_history(self) -> None:
        uid = uuid.uuid4()
        hist = [Message(role="user", content="a")]
        assert resolve_effective_history(uid, hist, None, None) == hist

    @patch("ai_backend.common.conversation_history.load_conversation_history_for_user")
    def test_uses_loaded_when_non_empty(self, mock_load: MagicMock) -> None:
        uid = uuid.uuid4()
        loaded = [Message(role="assistant", content="from db")]
        mock_load.return_value = loaded
        client = MagicMock()
        fallback = [Message(role="user", content="client")]
        out = resolve_effective_history(uid, fallback, 5, client)
        assert out == loaded
        mock_load.assert_called_once_with(uid, 5, client)

    @patch("ai_backend.common.conversation_history.load_conversation_history_for_user")
    def test_falls_back_when_load_empty(self, mock_load: MagicMock) -> None:
        uid = uuid.uuid4()
        mock_load.return_value = []
        fallback = [Message(role="user", content="c")]
        out = resolve_effective_history(uid, fallback, 5, MagicMock())
        assert out == fallback

    @patch(
        "ai_backend.common.conversation_history.load_conversation_history_for_user",
        side_effect=RuntimeError("boom"),
    )
    def test_exception_returns_request_history(self, _mock: MagicMock) -> None:
        uid = uuid.uuid4()
        fallback = [Message(role="user", content="safe")]
        out = resolve_effective_history(uid, fallback, 5, MagicMock())
        assert out == fallback
