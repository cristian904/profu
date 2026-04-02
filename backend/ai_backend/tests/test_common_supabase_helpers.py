"""
Unit tests for Supabase helper functions (quota, history).
"""

import uuid
from unittest.mock import MagicMock

from ai_backend.common.models import Message
from ai_backend.common.supabase_helpers import (
    get_solve_quota_count,
    load_conversation_history_for_user,
)


class TestGetSolveQuotaCount:
    """Tests for get_solve_quota_count."""

    def test_none_client_returns_zero(self) -> None:
        uid = uuid.uuid4()
        assert get_solve_quota_count(uid, None) == 0

    def test_list_response_first_element(self) -> None:
        uid = uuid.uuid4()
        rpc = MagicMock()
        rpc.execute.return_value = MagicMock(data=[5])
        client = MagicMock()
        client.rpc.return_value = rpc
        assert get_solve_quota_count(uid, client) == 5
        client.rpc.assert_called_once_with(
            "get_solve_conversations_count_current_month",
            {"p_user_id": str(uid)},
        )

    def test_int_response(self) -> None:
        uid = uuid.uuid4()
        rpc = MagicMock()
        rpc.execute.return_value = MagicMock(data=3)
        client = MagicMock()
        client.rpc.return_value = rpc
        assert get_solve_quota_count(uid, client) == 3

    def test_rpc_exception_returns_zero(self) -> None:
        uid = uuid.uuid4()
        client = MagicMock()
        client.rpc.side_effect = RuntimeError("db down")
        assert get_solve_quota_count(uid, client) == 0


class TestLoadConversationHistoryForUser:
    """Tests for load_conversation_history_for_user."""

    def test_none_client_empty(self) -> None:
        uid = uuid.uuid4()
        assert load_conversation_history_for_user(uid, 1, None) == []

    def test_no_conversation_row(self) -> None:
        uid = uuid.uuid4()
        client = MagicMock()
        t1 = MagicMock()
        t1.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        client.table.return_value = t1
        assert load_conversation_history_for_user(uid, 99, client) == []

    def test_wrong_owner_returns_empty(self) -> None:
        uid = uuid.uuid4()
        other = uuid.uuid4()
        client = MagicMock()
        conv_chain = MagicMock()
        conv_chain.execute.return_value = MagicMock(data=[{"id": 1, "user_id": str(other)}])
        client.table.return_value = conv_chain
        assert load_conversation_history_for_user(uid, 1, client) == []

    def test_loads_messages_mapped_roles(self) -> None:
        uid = uuid.uuid4()
        client = MagicMock()

        def table_side_effect(name: str) -> MagicMock:
            t = MagicMock()
            if name == "conversations":
                t.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                    data=[{"id": 10, "user_id": str(uid)}]
                )
            elif name == "conversation_messages":
                t.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
                    data=[
                        {"speaker": "user", "content": "Hi"},
                        {"speaker": "assistant", "content": "Hello"},
                    ]
                )
            return t

        client.table.side_effect = table_side_effect
        hist = load_conversation_history_for_user(uid, 10, client)
        assert hist == [
            Message(role="user", content="Hi"),
            Message(role="assistant", content="Hello"),
        ]
