"""
TDD tests for chat_splitter.py — Jaco's auto-topic-split feature.

Tests cover:
1. SplitResult dataclass
2. generate_context_summary — LLM-based context summary generation
3. generate_chat_title — LLM-based title generation
4. build_new_chat_data — construct new chat from split
5. record_topic_boundary — boundary metadata tracking
6. execute_chat_split — full split orchestration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from open_webui.utils.chat_splitter import (
    SplitResult,
    SplitConfig,
    TopicBoundary,
    generate_context_summary,
    generate_chat_title,
    build_new_chat_data,
    record_topic_boundary,
    execute_chat_split,
    CONTEXT_SUMMARY_PROMPT,
    TITLE_GENERATION_PROMPT,
)


class TestSplitResult:
    """Tests for SplitResult dataclass."""

    def test_defaults(self):
        r = SplitResult()
        assert r.success is False
        assert r.new_chat_id == ""
        assert r.new_chat_title == ""
        assert r.original_chat_new_title == ""
        assert r.context_summary == ""
        assert r.error is None

    def test_custom_values(self):
        r = SplitResult(
            success=True,
            new_chat_id="abc-123",
            new_chat_title="Machine Learning",
            original_chat_new_title="Cooking Recipes",
            context_summary="User was discussing cooking.",
        )
        assert r.success is True
        assert r.new_chat_id == "abc-123"


class TestSplitConfig:
    """Tests for SplitConfig defaults."""

    def test_defaults(self):
        c = SplitConfig()
        assert c.auto_title is True
        assert c.include_context_summary is True
        assert c.max_context_messages == 10
        assert c.context_summary_max_tokens == 200


class TestTopicBoundary:
    """Tests for TopicBoundary dataclass."""

    def test_defaults(self):
        b = TopicBoundary(
            original_chat_id="chat-1",
            new_chat_id="chat-2",
            triggering_message="Hello new topic",
            old_topic="Cooking",
            new_topic="Machine Learning",
        )
        assert b.original_chat_id == "chat-1"
        assert b.new_chat_id == "chat-2"
        assert b.split_timestamp > 0
        assert b.confidence == 0.0

    def test_to_dict(self):
        b = TopicBoundary(
            original_chat_id="c1",
            new_chat_id="c2",
            triggering_message="msg",
            old_topic="old",
            new_topic="new",
            confidence=0.9,
        )
        d = b.to_dict()
        assert d["original_chat_id"] == "c1"
        assert d["new_chat_id"] == "c2"
        assert d["confidence"] == 0.9
        assert "split_timestamp" in d


class TestGenerateContextSummary:
    """Tests for generate_context_summary."""

    @pytest.mark.asyncio
    async def test_basic_summary(self):
        mock_llm = AsyncMock(return_value="  User was asking about Python.  ")
        messages = [
            {"role": "user", "content": "How do I use Python?"},
            {"role": "assistant", "content": "Python is a programming language."},
        ]
        result = await generate_context_summary(messages, llm_call=mock_llm)
        assert result == "User was asking about Python."

    @pytest.mark.asyncio
    async def test_no_llm_returns_empty(self):
        result = await generate_context_summary(
            [{"role": "user", "content": "hi"}],
            llm_call=None,
        )
        assert result == ""

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty(self):
        mock_llm = AsyncMock(side_effect=RuntimeError("LLM down"))
        result = await generate_context_summary(
            [{"role": "user", "content": "hi"}],
            llm_call=mock_llm,
        )
        assert result == ""

    @pytest.mark.asyncio
    async def test_prompt_contains_messages(self):
        mock_llm = AsyncMock(return_value="summary")
        messages = [
            {"role": "user", "content": "Tell me about cats"},
            {"role": "assistant", "content": "Cats are great pets."},
        ]
        await generate_context_summary(messages, llm_call=mock_llm)
        prompt = mock_llm.call_args[0][0]
        assert "Tell me about cats" in prompt
        assert "Cats are great pets" in prompt

    @pytest.mark.asyncio
    async def test_max_messages_truncation(self):
        """Only last N messages should be included in the prompt."""
        mock_llm = AsyncMock(return_value="summary")
        messages = [{"role": "user", "content": f"msg{i}"} for i in range(20)]
        await generate_context_summary(
            messages, llm_call=mock_llm, max_messages=5
        )
        prompt = mock_llm.call_args[0][0]
        # Should contain last 5 messages
        assert "msg19" in prompt
        assert "msg15" in prompt
        # Should NOT contain old messages
        assert "msg0" not in prompt

    @pytest.mark.asyncio
    async def test_empty_messages_returns_empty(self):
        mock_llm = AsyncMock(return_value="summary")
        result = await generate_context_summary([], llm_call=mock_llm)
        assert result == ""


class TestGenerateChatTitle:
    """Tests for generate_chat_title."""

    @pytest.mark.asyncio
    async def test_basic_title_generation(self):
        mock_llm = AsyncMock(return_value="  Machine Learning Basics  ")
        result = await generate_chat_title(
            topic_hint="Machine Learning",
            recent_message="Tell me about neural networks",
            llm_call=mock_llm,
        )
        assert result == "Machine Learning Basics"

    @pytest.mark.asyncio
    async def test_no_llm_returns_hint(self):
        result = await generate_chat_title(
            topic_hint="Python Tips",
            recent_message="How to sort?",
            llm_call=None,
        )
        assert result == "Python Tips"

    @pytest.mark.asyncio
    async def test_llm_error_returns_hint(self):
        mock_llm = AsyncMock(side_effect=RuntimeError("LLM down"))
        result = await generate_chat_title(
            topic_hint="Cooking",
            recent_message="How to boil?",
            llm_call=mock_llm,
        )
        assert result == "Cooking"

    @pytest.mark.asyncio
    async def test_empty_hint_with_no_llm(self):
        result = await generate_chat_title(
            topic_hint="",
            recent_message="hello",
            llm_call=None,
        )
        assert result == "New Chat"

    @pytest.mark.asyncio
    async def test_prompt_contains_topic_and_message(self):
        mock_llm = AsyncMock(return_value="Title")
        await generate_chat_title(
            topic_hint="Cooking",
            recent_message="How to make pasta?",
            llm_call=mock_llm,
        )
        prompt = mock_llm.call_args[0][0]
        assert "Cooking" in prompt
        assert "How to make pasta?" in prompt


class TestBuildNewChatData:
    """Tests for build_new_chat_data."""

    def test_basic_build(self):
        result = build_new_chat_data(
            user_id="user-1",
            title="New Topic Chat",
            triggering_message={"role": "user", "content": "New topic here"},
            context_summary="Previous context about cooking.",
            parent_chat_id="chat-orig",
        )
        assert result["user_id"] == "user-1"
        assert result["title"] == "New Topic Chat"
        assert result["parent_chat_id"] == "chat-orig"
        assert result["split_summary"] == "Previous context about cooking."

    def test_messages_contain_triggering_message(self):
        msg = {"role": "user", "content": "Tell me about ML"}
        result = build_new_chat_data(
            user_id="u1",
            title="ML Chat",
            triggering_message=msg,
            context_summary="",
            parent_chat_id="c1",
        )
        chat_messages = result["chat"]["messages"]
        assert any(m["content"] == "Tell me about ML" for m in chat_messages)

    def test_context_summary_in_system_message(self):
        result = build_new_chat_data(
            user_id="u1",
            title="Chat",
            triggering_message={"role": "user", "content": "hi"},
            context_summary="Was discussing Python OOP patterns.",
            parent_chat_id="c1",
        )
        chat_messages = result["chat"]["messages"]
        system_msgs = [m for m in chat_messages if m["role"] == "system"]
        assert len(system_msgs) == 1
        assert "Python OOP patterns" in system_msgs[0]["content"]

    def test_no_system_message_when_no_context(self):
        result = build_new_chat_data(
            user_id="u1",
            title="Chat",
            triggering_message={"role": "user", "content": "hi"},
            context_summary="",
            parent_chat_id="c1",
        )
        chat_messages = result["chat"]["messages"]
        system_msgs = [m for m in chat_messages if m["role"] == "system"]
        assert len(system_msgs) == 0

    def test_has_new_chat_id(self):
        result = build_new_chat_data(
            user_id="u1",
            title="Chat",
            triggering_message={"role": "user", "content": "hi"},
            context_summary="",
            parent_chat_id="c1",
        )
        assert "id" in result
        assert len(result["id"]) > 0
        assert result["id"] != "c1"

    def test_timestamps_set(self):
        result = build_new_chat_data(
            user_id="u1",
            title="Chat",
            triggering_message={"role": "user", "content": "hi"},
            context_summary="",
            parent_chat_id="c1",
        )
        assert "created_at" in result
        assert "updated_at" in result
        assert result["created_at"] > 0


class TestRecordTopicBoundary:
    """Tests for record_topic_boundary."""

    def test_creates_boundary(self):
        boundary = record_topic_boundary(
            original_chat_id="c1",
            new_chat_id="c2",
            triggering_message="New topic msg",
            old_topic="Cooking",
            new_topic="Machine Learning",
            confidence=0.85,
        )
        assert isinstance(boundary, TopicBoundary)
        assert boundary.original_chat_id == "c1"
        assert boundary.new_chat_id == "c2"
        assert boundary.confidence == 0.85
        assert boundary.triggering_message == "New topic msg"

    def test_boundary_dict_serializable(self):
        import json

        boundary = record_topic_boundary(
            original_chat_id="c1",
            new_chat_id="c2",
            triggering_message="msg",
            old_topic="old",
            new_topic="new",
        )
        # Should not raise
        json.dumps(boundary.to_dict())


class TestExecuteChatSplit:
    """Tests for execute_chat_split orchestration function."""

    @pytest.mark.asyncio
    async def test_basic_split(self):
        mock_llm = AsyncMock(side_effect=[
            "User was discussing cooking recipes.",  # context summary
            "Machine Learning Basics",               # new chat title
            "Italian Cooking",                       # original chat title
        ])
        messages = [
            {"role": "user", "content": "How to make pasta?"},
            {"role": "assistant", "content": "Boil water first."},
            {"role": "user", "content": "Tell me about neural networks"},
        ]
        result = await execute_chat_split(
            original_chat_id="chat-1",
            user_id="user-1",
            messages=messages,
            triggering_message={"role": "user", "content": "Tell me about neural networks"},
            new_topic_name="Machine Learning",
            old_topic_name="Cooking",
            confidence=0.9,
            llm_call=mock_llm,
        )
        assert result.success is True
        assert result.new_chat_id != ""
        assert result.new_chat_title == "Machine Learning Basics"
        assert result.original_chat_new_title == "Italian Cooking"
        assert result.context_summary != ""

    @pytest.mark.asyncio
    async def test_split_without_llm(self):
        """Split should work without LLM, using fallback titles."""
        result = await execute_chat_split(
            original_chat_id="chat-1",
            user_id="user-1",
            messages=[
                {"role": "user", "content": "Old topic"},
                {"role": "assistant", "content": "Response"},
            ],
            triggering_message={"role": "user", "content": "New topic"},
            new_topic_name="New Topic",
            old_topic_name="Old Topic",
            confidence=0.8,
            llm_call=None,
        )
        assert result.success is True
        assert result.new_chat_title == "New Topic"
        assert result.original_chat_new_title == "Old Topic"

    @pytest.mark.asyncio
    async def test_split_returns_boundary(self):
        result = await execute_chat_split(
            original_chat_id="chat-1",
            user_id="user-1",
            messages=[{"role": "user", "content": "old"}],
            triggering_message={"role": "user", "content": "new"},
            new_topic_name="New",
            old_topic_name="Old",
            confidence=0.7,
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_split_config_no_auto_title(self):
        """When auto_title is False, use topic hints directly."""
        config = SplitConfig(auto_title=False)
        result = await execute_chat_split(
            original_chat_id="chat-1",
            user_id="user-1",
            messages=[{"role": "user", "content": "old"}],
            triggering_message={"role": "user", "content": "new"},
            new_topic_name="ML Topic",
            old_topic_name="Cook Topic",
            confidence=0.8,
            config=config,
        )
        assert result.new_chat_title == "ML Topic"
        assert result.original_chat_new_title == "Cook Topic"

    @pytest.mark.asyncio
    async def test_split_config_no_context_summary(self):
        """When include_context_summary is False, skip summary."""
        config = SplitConfig(include_context_summary=False)
        mock_llm = AsyncMock(side_effect=[
            "New Title",       # new chat title
            "Old Title",       # original chat title
        ])
        result = await execute_chat_split(
            original_chat_id="chat-1",
            user_id="user-1",
            messages=[{"role": "user", "content": "old"}],
            triggering_message={"role": "user", "content": "new"},
            new_topic_name="New",
            old_topic_name="Old",
            confidence=0.8,
            llm_call=mock_llm,
            config=config,
        )
        assert result.context_summary == ""

    @pytest.mark.asyncio
    async def test_split_new_chat_data_has_parent_id(self):
        """New chat should reference parent chat."""
        result = await execute_chat_split(
            original_chat_id="parent-chat-123",
            user_id="user-1",
            messages=[{"role": "user", "content": "old"}],
            triggering_message={"role": "user", "content": "new"},
            new_topic_name="New",
            old_topic_name="Old",
            confidence=0.8,
        )
        assert result.success is True
        assert result.new_chat_id != "parent-chat-123"

    @pytest.mark.asyncio
    async def test_llm_partial_failure_still_succeeds(self):
        """If some LLM calls fail, split should still succeed with fallbacks."""
        call_count = 0

        async def flaky_llm(prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "Good summary"
            raise RuntimeError("LLM flake")

        result = await execute_chat_split(
            original_chat_id="chat-1",
            user_id="user-1",
            messages=[{"role": "user", "content": "old"}],
            triggering_message={"role": "user", "content": "new"},
            new_topic_name="New Topic",
            old_topic_name="Old Topic",
            confidence=0.8,
            llm_call=flaky_llm,
        )
        assert result.success is True
        # Should fall back to hint names
        assert result.new_chat_title == "New Topic"

    @pytest.mark.asyncio
    async def test_context_summary_prompt_template(self):
        """CONTEXT_SUMMARY_PROMPT should have placeholder for messages."""
        assert "{conversation}" in CONTEXT_SUMMARY_PROMPT

    @pytest.mark.asyncio
    async def test_title_generation_prompt_template(self):
        """TITLE_GENERATION_PROMPT should have placeholders."""
        assert "{topic_hint}" in TITLE_GENERATION_PROMPT
        assert "{message}" in TITLE_GENERATION_PROMPT
