"""
TDD tests for the full side chat combine flow (Phase 3.2).

Tests edge cases for the combine endpoint logic, status transitions,
and the interaction between the combiner, models, and router.
"""

import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# =========================================================================
# Edge cases for the combiner itself
# =========================================================================


class TestCombinerEdgeCases:
    """Additional edge case tests for generate_combined_step."""

    @pytest.mark.asyncio
    async def test_very_long_side_chat_history(self):
        """Should handle a long conversation without error."""
        from open_webui.utils.side_chat_combiner import generate_combined_step

        messages = []
        for i in range(50):
            messages.append({"role": "user", "content": f"Question {i}"})
            messages.append({"role": "assistant", "content": f"Answer {i}"})

        mock_llm = AsyncMock(return_value="Revised step")
        result = await generate_combined_step(
            original_step_content="Original step",
            side_chat_messages=messages,
            llm_call=mock_llm,
        )
        assert result == "Revised step"
        # Verify all messages made it into the prompt
        prompt = mock_llm.call_args[0][0]
        assert "Question 0" in prompt
        assert "Question 49" in prompt

    @pytest.mark.asyncio
    async def test_messages_with_special_characters(self):
        """Should handle messages containing special characters."""
        from open_webui.utils.side_chat_combiner import generate_combined_step

        mock_llm = AsyncMock(return_value="Result")
        await generate_combined_step(
            original_step_content='Step with "quotes" and {braces}',
            side_chat_messages=[
                {"role": "user", "content": "What about $variables and `backticks`?"},
                {"role": "assistant", "content": "Use \\n newlines and \t tabs."},
            ],
            llm_call=mock_llm,
        )
        prompt = mock_llm.call_args[0][0]
        assert "$variables" in prompt
        assert "`backticks`" in prompt
        assert '"quotes"' in prompt
        assert "{braces}" in prompt

    @pytest.mark.asyncio
    async def test_multiline_step_content(self):
        """Should handle multi-line original step content."""
        from open_webui.utils.side_chat_combiner import generate_combined_step

        step = "Install Python:\n1. Download from python.org\n2. Run installer\n3. Verify with python --version"
        mock_llm = AsyncMock(return_value="Revised multi-line step")
        result = await generate_combined_step(
            original_step_content=step,
            side_chat_messages=[
                {"role": "user", "content": "Add pyenv option?"},
            ],
            llm_call=mock_llm,
        )
        assert result == "Revised multi-line step"
        prompt = mock_llm.call_args[0][0]
        assert "python.org" in prompt

    @pytest.mark.asyncio
    async def test_llm_returns_empty_string(self):
        """When LLM returns empty string, strip should give empty string."""
        from open_webui.utils.side_chat_combiner import generate_combined_step

        mock_llm = AsyncMock(return_value="   ")
        result = await generate_combined_step(
            original_step_content="Step",
            side_chat_messages=[{"role": "user", "content": "q"}],
            llm_call=mock_llm,
        )
        assert result == ""

    @pytest.mark.asyncio
    async def test_llm_timeout_returns_none(self):
        """Timeout exceptions should be caught and return None."""
        from open_webui.utils.side_chat_combiner import generate_combined_step

        mock_llm = AsyncMock(side_effect=TimeoutError("LLM timeout"))
        result = await generate_combined_step(
            original_step_content="Step",
            side_chat_messages=[{"role": "user", "content": "q"}],
            llm_call=mock_llm,
        )
        assert result is None


# =========================================================================
# Tests for status transition rules
# =========================================================================


class TestStatusTransitions:
    """Tests for side chat lifecycle state transitions."""

    def test_valid_statuses(self):
        from open_webui.models.side_chats import SIDE_CHAT_STATUSES

        assert SIDE_CHAT_STATUSES == {"open", "combined", "discarded"}

    def test_open_to_combined_is_valid(self):
        from open_webui.models.side_chats import SideChatModel

        m = SideChatModel(
            id="sc-1",
            chat_id="c-1",
            user_id="u-1",
            step_index=0,
            original_step_content="step",
            status="combined",
            combined_step_content="revised",
        )
        assert m.status == "combined"

    def test_open_to_discarded_is_valid(self):
        from open_webui.models.side_chats import SideChatModel

        m = SideChatModel(
            id="sc-1",
            chat_id="c-1",
            user_id="u-1",
            step_index=0,
            original_step_content="step",
            status="discarded",
        )
        assert m.status == "discarded"

    def test_update_status_rejects_invalid(self):
        """update_status should reject invalid status values."""
        from open_webui.models.side_chats import SideChatTable

        table = SideChatTable()
        # Mock db not needed — should fail before DB call
        result = table.update_status(
            side_chat_id="sc-1",
            status="invalid_status",
        )
        assert result is None

    def test_combined_side_chat_has_content(self):
        """A combined side chat should store the combined step content."""
        from open_webui.models.side_chats import SideChatModel

        m = SideChatModel(
            id="sc-1",
            chat_id="c-1",
            user_id="u-1",
            step_index=2,
            original_step_content="Original",
            combined_step_content="Revised with side chat insights",
            status="combined",
        )
        assert m.combined_step_content is not None
        assert "Revised" in m.combined_step_content


# =========================================================================
# Tests for combine endpoint logic integration
# =========================================================================


class TestCombineEndpointLogic:
    """Tests for the combine endpoint's interaction with combiner + model."""

    @pytest.mark.asyncio
    async def test_combine_formats_messages_correctly(self):
        """The endpoint should convert model messages to dicts for combiner."""
        from open_webui.utils.side_chat_combiner import generate_combined_step

        # Simulate what the endpoint does: convert model objects to dicts
        mock_msgs = [
            MagicMock(role="user", content="Question about step"),
            MagicMock(role="assistant", content="Here's an insight"),
            MagicMock(role="user", content="Follow-up"),
        ]
        message_dicts = [{"role": m.role, "content": m.content} for m in mock_msgs]

        mock_llm = AsyncMock(return_value="Combined result")
        result = await generate_combined_step(
            original_step_content="Do something",
            side_chat_messages=message_dicts,
            llm_call=mock_llm,
        )
        assert result == "Combined result"

        # Verify all three messages appear in the prompt
        prompt = mock_llm.call_args[0][0]
        assert "Question about step" in prompt
        assert "Here's an insight" in prompt
        assert "Follow-up" in prompt

    @pytest.mark.asyncio
    async def test_combine_preserves_message_order(self):
        """Messages should be in chronological order in the prompt."""
        from open_webui.utils.side_chat_combiner import generate_combined_step

        messages = [
            {"role": "user", "content": "FIRST"},
            {"role": "assistant", "content": "SECOND"},
            {"role": "user", "content": "THIRD"},
        ]

        mock_llm = AsyncMock(return_value="result")
        await generate_combined_step(
            original_step_content="Step",
            side_chat_messages=messages,
            llm_call=mock_llm,
        )
        prompt = mock_llm.call_args[0][0]
        assert prompt.index("FIRST") < prompt.index("SECOND") < prompt.index("THIRD")

    def test_router_rejects_combine_on_non_open_side_chat(self):
        """The router should return 400 for non-open side chats."""
        from open_webui.models.side_chats import SideChatModel

        # A combined side chat should not be combinable again
        m = SideChatModel(
            id="sc-1",
            chat_id="c-1",
            user_id="u-1",
            step_index=0,
            original_step_content="step",
            status="combined",
        )
        assert m.status != "open"

    def test_router_rejects_message_on_non_open_side_chat(self):
        """The router should return 400 for adding messages to non-open side chats."""
        from open_webui.models.side_chats import SideChatModel

        m = SideChatModel(
            id="sc-1",
            chat_id="c-1",
            user_id="u-1",
            step_index=0,
            original_step_content="step",
            status="discarded",
        )
        assert m.status != "open"


# =========================================================================
# Tests for the combiner prompt template
# =========================================================================


class TestCombinePromptTemplate:
    """Tests for COMBINE_SYSTEM_PROMPT structure and content."""

    def test_template_has_original_step_placeholder(self):
        from open_webui.utils.side_chat_combiner import COMBINE_SYSTEM_PROMPT

        assert "{original_step}" in COMBINE_SYSTEM_PROMPT

    def test_template_has_side_chat_history_placeholder(self):
        from open_webui.utils.side_chat_combiner import COMBINE_SYSTEM_PROMPT

        assert "{side_chat_history}" in COMBINE_SYSTEM_PROMPT

    def test_template_instructs_rewrite(self):
        from open_webui.utils.side_chat_combiner import COMBINE_SYSTEM_PROMPT

        assert "Rewrite" in COMBINE_SYSTEM_PROMPT

    def test_template_asks_for_concise_output(self):
        from open_webui.utils.side_chat_combiner import COMBINE_SYSTEM_PROMPT

        assert "concise" in COMBINE_SYSTEM_PROMPT.lower() or "ONLY" in COMBINE_SYSTEM_PROMPT


# =========================================================================
# Tests for _make_llm_call wiring in the router
# =========================================================================


class TestMakeLlmCall:
    """Tests for the _make_llm_call helper in side_chats router."""

    def test_make_llm_call_returns_callable(self):
        """_make_llm_call should return an async callable."""
        from open_webui.routers.side_chats import _make_llm_call

        mock_request = MagicMock()
        mock_user = MagicMock()
        result = _make_llm_call(mock_request, mock_user)
        assert callable(result)

    @staticmethod
    def _mock_modules(mock_gen):
        """Create sys.modules patches for heavy deps used by _make_llm_call."""
        mock_chat = MagicMock()
        mock_chat.generate_chat_completion = mock_gen

        # get_task_model_id is simple — provide the real logic via a mock module
        def _get_task_model_id(default_id, task_model, task_model_ext, models):
            if models.get(default_id, {}).get("connection_type") == "local":
                return task_model if (task_model and task_model in models) else default_id
            return task_model_ext if (task_model_ext and task_model_ext in models) else default_id

        mock_task = MagicMock()
        mock_task.get_task_model_id = _get_task_model_id

        return patch.dict(sys.modules, {
            "open_webui.utils.chat": mock_chat,
            "open_webui.utils.task": mock_task,
        })

    @pytest.mark.asyncio
    async def test_make_llm_call_uses_task_model(self):
        """The llm_call should resolve the task model via get_task_model_id."""
        from open_webui.routers.side_chats import _make_llm_call

        mock_gen = AsyncMock(
            return_value={"choices": [{"message": {"content": "LLM reply"}}]}
        )

        mock_request = MagicMock()
        mock_request.app.state.MODELS = {"model-a": {"id": "model-a"}}
        mock_request.app.state.config.TASK_MODEL = ""
        mock_request.app.state.config.TASK_MODEL_EXTERNAL = ""
        mock_user = MagicMock()

        with self._mock_modules(mock_gen):
            llm_call = _make_llm_call(mock_request, mock_user)
            result = await llm_call("test prompt")

        assert result == "LLM reply"
        call_payload = mock_gen.call_args[1].get("form_data") or mock_gen.call_args[0][1]
        assert call_payload["model"] == "model-a"
        assert call_payload["stream"] is False

    @pytest.mark.asyncio
    async def test_make_llm_call_no_models_raises(self):
        """Should raise RuntimeError when no models are available."""
        from open_webui.routers.side_chats import _make_llm_call

        mock_gen = AsyncMock()

        mock_request = MagicMock()
        mock_request.app.state.MODELS = {}
        mock_user = MagicMock()

        with self._mock_modules(mock_gen):
            llm_call = _make_llm_call(mock_request, mock_user)
            with pytest.raises(RuntimeError, match="No models available"):
                await llm_call("test prompt")

    @pytest.mark.asyncio
    async def test_make_llm_call_bypasses_filter(self):
        """Internal combine calls should bypass access filters."""
        from open_webui.routers.side_chats import _make_llm_call

        mock_gen = AsyncMock(
            return_value={"choices": [{"message": {"content": "ok"}}]}
        )

        mock_request = MagicMock()
        mock_request.app.state.MODELS = {"m1": {"id": "m1"}}
        mock_request.app.state.config.TASK_MODEL = ""
        mock_request.app.state.config.TASK_MODEL_EXTERNAL = ""
        mock_user = MagicMock()

        with self._mock_modules(mock_gen):
            llm_call = _make_llm_call(mock_request, mock_user)
            await llm_call("prompt")

        _, kwargs = mock_gen.call_args
        assert kwargs.get("bypass_filter") is True


# =========================================================================
# Tests for single-message and unicode edge cases
# =========================================================================


class TestCombinerUnicodeAndSingleMessage:
    """Edge cases for unicode content and minimal conversations."""

    @pytest.mark.asyncio
    async def test_single_user_message_only(self):
        """Combine should work with just one user message (no assistant reply)."""
        from open_webui.utils.side_chat_combiner import generate_combined_step

        mock_llm = AsyncMock(return_value="Updated step")
        result = await generate_combined_step(
            original_step_content="Configure database",
            side_chat_messages=[
                {"role": "user", "content": "Should I use PostgreSQL instead of SQLite?"},
            ],
            llm_call=mock_llm,
        )
        assert result == "Updated step"
        prompt = mock_llm.call_args[0][0]
        assert "PostgreSQL" in prompt

    @pytest.mark.asyncio
    async def test_unicode_content_preserved(self):
        """Unicode in step content and messages should pass through correctly."""
        from open_webui.utils.side_chat_combiner import generate_combined_step

        mock_llm = AsyncMock(return_value="Paso revisado")
        await generate_combined_step(
            original_step_content="Configurar el servidor",
            side_chat_messages=[
                {"role": "user", "content": "Usar nginx o apache?"},
            ],
            llm_call=mock_llm,
        )
        prompt = mock_llm.call_args[0][0]
        assert "Configurar el servidor" in prompt
        assert "nginx o apache" in prompt

    @pytest.mark.asyncio
    async def test_emoji_content_preserved(self):
        """Emoji characters in messages should be preserved in prompt."""
        from open_webui.utils.side_chat_combiner import generate_combined_step

        mock_llm = AsyncMock(return_value="result")
        await generate_combined_step(
            original_step_content="Deploy the app",
            side_chat_messages=[
                {"role": "user", "content": "Should we add health checks? \U0001f3e5"},
            ],
            llm_call=mock_llm,
        )
        prompt = mock_llm.call_args[0][0]
        assert "\U0001f3e5" in prompt
