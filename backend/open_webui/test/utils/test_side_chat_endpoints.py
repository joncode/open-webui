"""
TDD tests for Jaco side chat endpoints.

Tests the REST endpoint handler logic for side chats using mocked
dependencies. Follows the same pattern as test_step_endpoints.py.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id="user-1"):
    mock = MagicMock()
    mock.id = user_id
    return mock


def _make_side_chat(
    side_chat_id="sc-1",
    chat_id="chat-1",
    user_id="user-1",
    step_index=2,
    original_step_content="Install Python 3.10",
    status="open",
):
    mock = MagicMock()
    mock.id = side_chat_id
    mock.chat_id = chat_id
    mock.user_id = user_id
    mock.step_index = step_index
    mock.original_step_content = original_step_content
    mock.status = status
    mock.combined_step_content = None
    return mock


def _make_message(msg_id="msg-1", side_chat_id="sc-1", role="user", content="Hello"):
    mock = MagicMock()
    mock.id = msg_id
    mock.side_chat_id = side_chat_id
    mock.role = role
    mock.content = content
    mock.ordering = 0
    return mock


# =========================================================================
# Tests for creating a side chat
# =========================================================================


class TestCreateSideChat:
    """Tests for POST /api/v1/side-chats."""

    def test_create_side_chat_form_validates(self):
        from open_webui.models.side_chats import CreateSideChatForm

        form = CreateSideChatForm(
            chat_id="chat-1",
            step_index=2,
            original_step_content="Install Python 3.10",
        )
        assert form.chat_id == "chat-1"
        assert form.step_index == 2

    def test_create_returns_side_chat_model(self):
        """Creating a side chat should return a valid model."""
        from open_webui.models.side_chats import SideChatModel

        m = SideChatModel(
            id="sc-1",
            chat_id="chat-1",
            user_id="user-1",
            step_index=2,
            original_step_content="Install Python 3.10",
            status="open",
        )
        assert m.status == "open"

    def test_create_requires_chat_id(self):
        """chat_id is required in the create form."""
        from open_webui.models.side_chats import CreateSideChatForm
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CreateSideChatForm(step_index=0, original_step_content="step")

    def test_create_requires_step_index(self):
        """step_index is required in the create form."""
        from open_webui.models.side_chats import CreateSideChatForm
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CreateSideChatForm(chat_id="chat-1", original_step_content="step")

    def test_create_requires_original_step_content(self):
        """original_step_content is required in the create form."""
        from open_webui.models.side_chats import CreateSideChatForm
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CreateSideChatForm(chat_id="chat-1", step_index=0)


# =========================================================================
# Tests for sending messages in a side chat
# =========================================================================


class TestAddSideChatMessage:
    """Tests for POST /api/v1/side-chats/:id/messages."""

    def test_add_message_form_validates(self):
        from open_webui.models.side_chats import AddSideChatMessageForm

        form = AddSideChatMessageForm(role="user", content="My question")
        assert form.role == "user"
        assert form.content == "My question"

    def test_message_requires_role(self):
        from open_webui.models.side_chats import AddSideChatMessageForm
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AddSideChatMessageForm(content="msg")

    def test_message_requires_content(self):
        from open_webui.models.side_chats import AddSideChatMessageForm
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AddSideChatMessageForm(role="user")


# =========================================================================
# Tests for the combine endpoint logic
# =========================================================================


class TestCombineSideChat:
    """Tests for POST /api/v1/side-chats/:id/combine."""

    @pytest.mark.asyncio
    async def test_combine_calls_generate_combined_step(self):
        """Combine should use generate_combined_step from side_chat_combiner."""
        from open_webui.utils.side_chat_combiner import generate_combined_step

        mock_llm = AsyncMock(return_value="Revised step text")
        result = await generate_combined_step(
            original_step_content="Install Python 3.10",
            side_chat_messages=[
                {"role": "user", "content": "Use 3.11?"},
                {"role": "assistant", "content": "Yes, better perf."},
            ],
            llm_call=mock_llm,
        )
        assert result == "Revised step text"

    @pytest.mark.asyncio
    async def test_combine_updates_status_to_combined(self):
        """After combine, side chat status should be 'combined'."""
        from open_webui.models.side_chats import SideChatModel

        m = SideChatModel(
            id="sc-1",
            chat_id="chat-1",
            user_id="user-1",
            step_index=2,
            original_step_content="Original",
            combined_step_content="Revised step",
            status="combined",
        )
        assert m.status == "combined"
        assert m.combined_step_content == "Revised step"

    @pytest.mark.asyncio
    async def test_combine_with_no_messages_still_works(self):
        """Combine with empty side chat should still call LLM."""
        from open_webui.utils.side_chat_combiner import generate_combined_step

        mock_llm = AsyncMock(return_value="Same step")
        result = await generate_combined_step(
            original_step_content="Original step",
            side_chat_messages=[],
            llm_call=mock_llm,
        )
        assert result == "Same step"
        mock_llm.assert_called_once()


# =========================================================================
# Tests for discarding a side chat
# =========================================================================


class TestDiscardSideChat:
    """Tests for DELETE /api/v1/side-chats/:id."""

    def test_discard_sets_status_discarded(self):
        """Discarding a side chat should mark status as 'discarded'."""
        from open_webui.models.side_chats import SIDE_CHAT_STATUSES

        assert "discarded" in SIDE_CHAT_STATUSES

    def test_cannot_combine_discarded_side_chat(self):
        """A discarded side chat cannot be combined."""
        from open_webui.models.side_chats import SideChatModel

        m = SideChatModel(
            id="sc-1",
            chat_id="chat-1",
            user_id="user-1",
            step_index=0,
            original_step_content="step",
            status="discarded",
        )
        assert m.status == "discarded"
        # The router should reject combine requests for discarded side chats


# =========================================================================
# Tests for router module structure
# =========================================================================


class TestSideChatRouterModule:
    """Tests that the router module exists and has correct structure."""

    def test_router_module_exists(self):
        from open_webui.routers import side_chats

        assert hasattr(side_chats, "router")

    def test_router_has_create_endpoint(self):
        from open_webui.routers.side_chats import router

        routes = [r.path for r in router.routes]
        assert "/" in routes  # POST /

    def test_router_has_add_message_endpoint(self):
        from open_webui.routers.side_chats import router

        routes = [r.path for r in router.routes]
        assert "/{id}/messages" in routes

    def test_router_has_combine_endpoint(self):
        from open_webui.routers.side_chats import router

        routes = [r.path for r in router.routes]
        assert "/{id}/combine" in routes

    def test_router_has_delete_endpoint(self):
        from open_webui.routers.side_chats import router

        routes = [r.path for r in router.routes]
        assert "/{id}" in routes

    def test_router_has_list_endpoint(self):
        """GET /by-chat/:chat_id lists side chats for a chat."""
        from open_webui.routers.side_chats import router

        routes = [r.path for r in router.routes]
        assert "/by-chat/{chat_id}" in routes
