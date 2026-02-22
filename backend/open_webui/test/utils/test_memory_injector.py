"""TDD tests for utils/memory_injector.py — Phase 4.1

The memory injector retrieves relevant user memories and formats them
for injection into the LLM system prompt.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
from open_webui.utils.memory_injector import (
    build_memory_context,
    format_memories_for_prompt,
    MEMORY_PREAMBLE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _memory(content, created_at=1000000):
    """Build a minimal memory-like dict."""
    return {"id": f"mem-{hash(content) % 10000}", "content": content, "created_at": created_at}


SAMPLE_MEMORIES = [
    _memory("User lives in Berlin"),
    _memory("User is a software engineer"),
    _memory("User prefers VS Code"),
    _memory("User works with Python and TypeScript"),
]


# ===========================================================================
class TestFormatMemoriesForPrompt:
    """Pure formatting — no async, no queries."""

    def test_basic_formatting(self):
        result = format_memories_for_prompt(SAMPLE_MEMORIES)

        assert MEMORY_PREAMBLE in result
        assert "User lives in Berlin" in result
        assert "User prefers VS Code" in result

    def test_empty_memories_returns_empty_string(self):
        result = format_memories_for_prompt([])

        assert result == ""

    def test_none_memories_returns_empty_string(self):
        result = format_memories_for_prompt(None)

        assert result == ""

    def test_memories_are_bullet_pointed(self):
        result = format_memories_for_prompt(SAMPLE_MEMORIES)

        lines = [l.strip() for l in result.split("\n") if l.strip().startswith("- ")]
        assert len(lines) == 4

    def test_max_memories_respected(self):
        many = [_memory(f"Fact {i}") for i in range(50)]

        result = format_memories_for_prompt(many, max_memories=10)

        lines = [l.strip() for l in result.split("\n") if l.strip().startswith("- ")]
        assert len(lines) == 10

    def test_default_max_is_20(self):
        many = [_memory(f"Fact {i}") for i in range(30)]

        result = format_memories_for_prompt(many)

        lines = [l.strip() for l in result.split("\n") if l.strip().startswith("- ")]
        assert len(lines) == 20


# ===========================================================================
class TestBuildMemoryContext:
    """Full pipeline: query memories then format."""

    @pytest.mark.asyncio
    async def test_basic_context_build(self):
        query_fn = AsyncMock(return_value=SAMPLE_MEMORIES)

        result = await build_memory_context(
            user_id="user-1",
            conversation_text="Tell me about Berlin",
            query_fn=query_fn,
        )

        assert "User lives in Berlin" in result
        query_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_fn_receives_user_id_and_text(self):
        query_fn = AsyncMock(return_value=[])

        await build_memory_context(
            user_id="user-42",
            conversation_text="What should I code today?",
            query_fn=query_fn,
        )

        call_kwargs = query_fn.call_args
        # The query function should receive user_id and query text
        args = call_kwargs[0] if call_kwargs[0] else ()
        kwargs = call_kwargs[1] if call_kwargs[1] else {}
        all_args = list(args) + list(kwargs.values())
        assert "user-42" in all_args
        assert "What should I code today?" in all_args

    @pytest.mark.asyncio
    async def test_no_memories_returns_empty(self):
        query_fn = AsyncMock(return_value=[])

        result = await build_memory_context(
            user_id="user-1",
            conversation_text="hi",
            query_fn=query_fn,
        )

        assert result == ""

    @pytest.mark.asyncio
    async def test_query_fn_error_returns_empty(self):
        query_fn = AsyncMock(side_effect=RuntimeError("DB down"))

        result = await build_memory_context(
            user_id="user-1",
            conversation_text="hello",
            query_fn=query_fn,
        )

        assert result == ""

    @pytest.mark.asyncio
    async def test_max_memories_passed_through(self):
        many = [_memory(f"Fact {i}") for i in range(30)]
        query_fn = AsyncMock(return_value=many)

        result = await build_memory_context(
            user_id="user-1",
            conversation_text="stuff",
            query_fn=query_fn,
            max_memories=5,
        )

        lines = [l.strip() for l in result.split("\n") if l.strip().startswith("- ")]
        assert len(lines) == 5


# ===========================================================================
class TestMemoryPreamble:
    """Verify the preamble is sensible."""

    def test_preamble_exists(self):
        assert isinstance(MEMORY_PREAMBLE, str)
        assert len(MEMORY_PREAMBLE) > 10

    def test_preamble_indicates_user_context(self):
        lower = MEMORY_PREAMBLE.lower()
        assert "user" in lower or "know" in lower or "remember" in lower
