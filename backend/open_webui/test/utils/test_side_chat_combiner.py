import pytest
from unittest.mock import AsyncMock

from open_webui.utils.side_chat_combiner import (
    generate_combined_step,
    COMBINE_SYSTEM_PROMPT,
)


class TestGenerateCombinedStep:
    """Tests for generate_combined_step async function."""

    @pytest.mark.asyncio
    async def test_basic_combine(self):
        mock_llm = AsyncMock(return_value="  Revised step with insights.  ")
        result = await generate_combined_step(
            original_step_content="Install Python 3.10",
            side_chat_messages=[
                {"role": "user", "content": "Should I use 3.11 instead?"},
                {"role": "assistant", "content": "Yes, 3.11 has better performance."},
            ],
            llm_call=mock_llm,
        )
        assert result == "Revised step with insights."
        mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_llm_call_returns_none(self):
        result = await generate_combined_step(
            original_step_content="Some step",
            side_chat_messages=[{"role": "user", "content": "Question"}],
            llm_call=None,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_llm_exception_returns_none(self):
        mock_llm = AsyncMock(side_effect=RuntimeError("LLM error"))
        result = await generate_combined_step(
            original_step_content="Some step",
            side_chat_messages=[{"role": "user", "content": "Question"}],
            llm_call=mock_llm,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_prompt_contains_original_step(self):
        mock_llm = AsyncMock(return_value="result")
        await generate_combined_step(
            original_step_content="Run npm install",
            side_chat_messages=[
                {"role": "user", "content": "Use yarn?"},
            ],
            llm_call=mock_llm,
        )
        prompt = mock_llm.call_args[0][0]
        assert "Run npm install" in prompt

    @pytest.mark.asyncio
    async def test_prompt_contains_side_chat_history(self):
        mock_llm = AsyncMock(return_value="result")
        await generate_combined_step(
            original_step_content="Step text",
            side_chat_messages=[
                {"role": "user", "content": "What about TypeScript?"},
                {"role": "assistant", "content": "Good idea, use TS."},
            ],
            llm_call=mock_llm,
        )
        prompt = mock_llm.call_args[0][0]
        assert "User: What about TypeScript?" in prompt
        assert "Jaco: Good idea, use TS." in prompt

    @pytest.mark.asyncio
    async def test_role_mapping_user(self):
        """User role should map to 'User' label."""
        mock_llm = AsyncMock(return_value="result")
        await generate_combined_step(
            original_step_content="Step",
            side_chat_messages=[{"role": "user", "content": "msg"}],
            llm_call=mock_llm,
        )
        prompt = mock_llm.call_args[0][0]
        assert "User: msg" in prompt

    @pytest.mark.asyncio
    async def test_role_mapping_assistant(self):
        """Assistant role should map to 'Jaco' label."""
        mock_llm = AsyncMock(return_value="result")
        await generate_combined_step(
            original_step_content="Step",
            side_chat_messages=[{"role": "assistant", "content": "reply"}],
            llm_call=mock_llm,
        )
        prompt = mock_llm.call_args[0][0]
        assert "Jaco: reply" in prompt

    @pytest.mark.asyncio
    async def test_role_mapping_system(self):
        """Non-user roles should map to 'Jaco' label."""
        mock_llm = AsyncMock(return_value="result")
        await generate_combined_step(
            original_step_content="Step",
            side_chat_messages=[{"role": "system", "content": "sys msg"}],
            llm_call=mock_llm,
        )
        prompt = mock_llm.call_args[0][0]
        assert "Jaco: sys msg" in prompt

    @pytest.mark.asyncio
    async def test_empty_side_chat_messages(self):
        mock_llm = AsyncMock(return_value="unchanged step")
        result = await generate_combined_step(
            original_step_content="Original step",
            side_chat_messages=[],
            llm_call=mock_llm,
        )
        assert result == "unchanged step"
        # Should still call LLM even with empty side chat
        mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_strips_result_whitespace(self):
        mock_llm = AsyncMock(return_value="\n  Result with whitespace  \n\n")
        result = await generate_combined_step(
            original_step_content="Step",
            side_chat_messages=[{"role": "user", "content": "q"}],
            llm_call=mock_llm,
        )
        assert result == "Result with whitespace"

    @pytest.mark.asyncio
    async def test_multiple_messages_in_order(self):
        mock_llm = AsyncMock(return_value="result")
        messages = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Second question"},
            {"role": "assistant", "content": "Second answer"},
        ]
        await generate_combined_step(
            original_step_content="Step",
            side_chat_messages=messages,
            llm_call=mock_llm,
        )
        prompt = mock_llm.call_args[0][0]
        # Verify ordering is preserved
        first_q_pos = prompt.index("First question")
        first_a_pos = prompt.index("First answer")
        second_q_pos = prompt.index("Second question")
        second_a_pos = prompt.index("Second answer")
        assert first_q_pos < first_a_pos < second_q_pos < second_a_pos

    @pytest.mark.asyncio
    async def test_prompt_uses_combine_system_prompt_template(self):
        """Verify the prompt follows the COMBINE_SYSTEM_PROMPT template."""
        mock_llm = AsyncMock(return_value="result")
        await generate_combined_step(
            original_step_content="My step content",
            side_chat_messages=[{"role": "user", "content": "My question"}],
            llm_call=mock_llm,
        )
        prompt = mock_llm.call_args[0][0]
        # Should contain the template markers
        assert "Original step:" in prompt
        assert "Side discussion:" in prompt
        assert "My step content" in prompt
        assert "Rewrite the original step" in prompt
