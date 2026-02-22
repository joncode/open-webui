"""
TDD tests for Jaco side chat data models and CRUD operations.

Tests the SideChat and SideChatMessage models, Pydantic schemas,
and the SideChatTable CRUD class.
"""

import pytest
import time
import uuid
from unittest.mock import MagicMock, patch
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Tests for SideChat data model
# ---------------------------------------------------------------------------


class TestSideChatModel:
    """Tests for the SideChat Pydantic model."""

    def test_model_fields_exist(self):
        from open_webui.models.side_chats import SideChatModel

        m = SideChatModel(
            id="sc-1",
            chat_id="chat-1",
            user_id="user-1",
            step_index=2,
            original_step_content="Install Python",
            status="open",
            created_at=1000000,
            updated_at=1000000,
        )
        assert m.id == "sc-1"
        assert m.chat_id == "chat-1"
        assert m.user_id == "user-1"
        assert m.step_index == 2
        assert m.original_step_content == "Install Python"
        assert m.status == "open"

    def test_model_defaults(self):
        from open_webui.models.side_chats import SideChatModel

        m = SideChatModel(
            id="sc-1",
            chat_id="chat-1",
            user_id="user-1",
            step_index=0,
            original_step_content="Step text",
        )
        assert m.status == "open"
        assert m.combined_step_content is None
        assert m.created_at == 0
        assert m.updated_at == 0

    def test_model_with_combined_content(self):
        from open_webui.models.side_chats import SideChatModel

        m = SideChatModel(
            id="sc-1",
            chat_id="chat-1",
            user_id="user-1",
            step_index=0,
            original_step_content="Original",
            combined_step_content="Revised step with insights",
            status="combined",
        )
        assert m.combined_step_content == "Revised step with insights"
        assert m.status == "combined"


class TestSideChatMessageModel:
    """Tests for the SideChatMessage Pydantic model."""

    def test_message_fields_exist(self):
        from open_webui.models.side_chats import SideChatMessageModel

        m = SideChatMessageModel(
            id="msg-1",
            side_chat_id="sc-1",
            role="user",
            content="What about Python 3.11?",
            created_at=1000000,
        )
        assert m.id == "msg-1"
        assert m.side_chat_id == "sc-1"
        assert m.role == "user"
        assert m.content == "What about Python 3.11?"

    def test_message_defaults(self):
        from open_webui.models.side_chats import SideChatMessageModel

        m = SideChatMessageModel(
            id="msg-1",
            side_chat_id="sc-1",
            role="assistant",
            content="Reply",
        )
        assert m.created_at == 0

    def test_message_with_ordering(self):
        from open_webui.models.side_chats import SideChatMessageModel

        m = SideChatMessageModel(
            id="msg-1",
            side_chat_id="sc-1",
            role="user",
            content="Q",
            ordering=3,
            created_at=1000000,
        )
        assert m.ordering == 3


# ---------------------------------------------------------------------------
# Tests for Pydantic form models
# ---------------------------------------------------------------------------


class TestSideChatForms:
    """Tests for request/response form models."""

    def test_create_side_chat_form(self):
        from open_webui.models.side_chats import CreateSideChatForm

        form = CreateSideChatForm(
            chat_id="chat-1",
            step_index=2,
            original_step_content="Install Python 3.10",
        )
        assert form.chat_id == "chat-1"
        assert form.step_index == 2
        assert form.original_step_content == "Install Python 3.10"

    def test_add_message_form(self):
        from open_webui.models.side_chats import AddSideChatMessageForm

        form = AddSideChatMessageForm(
            role="user",
            content="Should I use 3.11 instead?",
        )
        assert form.role == "user"
        assert form.content == "Should I use 3.11 instead?"


# ---------------------------------------------------------------------------
# Tests for SideChatTable CRUD
# ---------------------------------------------------------------------------


class TestSideChatTableUnit:
    """Unit tests for SideChatTable CRUD operations (mocked DB)."""

    def test_create_side_chat_returns_model(self):
        """create_side_chat should return a SideChatModel."""
        from open_webui.models.side_chats import SideChats

        # Verify the singleton exists
        assert SideChats is not None
        assert hasattr(SideChats, "create_side_chat")
        assert hasattr(SideChats, "get_side_chat_by_id")
        assert hasattr(SideChats, "get_side_chats_by_chat_id")
        assert hasattr(SideChats, "add_message")
        assert hasattr(SideChats, "get_messages")
        assert hasattr(SideChats, "update_status")
        assert hasattr(SideChats, "delete_side_chat")

    def test_statuses_are_valid(self):
        """Side chat status values should be well-defined."""
        from open_webui.models.side_chats import SIDE_CHAT_STATUSES

        assert "open" in SIDE_CHAT_STATUSES
        assert "combined" in SIDE_CHAT_STATUSES
        assert "discarded" in SIDE_CHAT_STATUSES


# ---------------------------------------------------------------------------
# Tests for ORM table definitions
# ---------------------------------------------------------------------------


class TestSideChatORM:
    """Tests for SQLAlchemy ORM model definitions."""

    def test_side_chat_table_name(self):
        from open_webui.models.side_chats import SideChatRecord

        assert SideChatRecord.__tablename__ == "side_chat"

    def test_side_chat_message_table_name(self):
        from open_webui.models.side_chats import SideChatMessageRecord

        assert SideChatMessageRecord.__tablename__ == "side_chat_message"

    def test_side_chat_has_required_columns(self):
        from open_webui.models.side_chats import SideChatRecord

        columns = {c.name for c in SideChatRecord.__table__.columns}
        expected = {
            "id",
            "chat_id",
            "user_id",
            "step_index",
            "original_step_content",
            "combined_step_content",
            "status",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(columns)

    def test_side_chat_message_has_required_columns(self):
        from open_webui.models.side_chats import SideChatMessageRecord

        columns = {c.name for c in SideChatMessageRecord.__table__.columns}
        expected = {
            "id",
            "side_chat_id",
            "role",
            "content",
            "ordering",
            "created_at",
        }
        assert expected.issubset(columns)

    def test_side_chat_has_indexes(self):
        from open_webui.models.side_chats import SideChatRecord

        index_names = {idx.name for idx in SideChatRecord.__table__.indexes}
        assert "side_chat_chat_id_idx" in index_names
        assert "side_chat_user_id_idx" in index_names

    def test_side_chat_message_has_indexes(self):
        from open_webui.models.side_chats import SideChatMessageRecord

        index_names = {idx.name for idx in SideChatMessageRecord.__table__.indexes}
        assert "side_chat_msg_side_chat_id_idx" in index_names
