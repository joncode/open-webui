"""TDD tests for utils/fact_extractor.py — Phase 4.1

The fact extractor takes recent conversation messages and uses an LLM call
to extract personal facts about the user.  Each fact has:
  - content:    plain-text statement (e.g. "User lives in Berlin")
  - category:   one of a fixed set (preference, biographical, technical, …)
  - confidence: float 0-1
"""

import json
import pytest
from unittest.mock import AsyncMock


# ---------------------------------------------------------------------------
# Import the module under test (will be created next)
# ---------------------------------------------------------------------------
from open_webui.utils.fact_extractor import (
    extract_facts,
    FACT_EXTRACTION_PROMPT,
    VALID_CATEGORIES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _msgs(pairs):
    """Build a list of {role, content} dicts from (role, text) tuples."""
    return [{"role": r, "content": c} for r, c in pairs]


SAMPLE_CONVERSATION = _msgs([
    ("user", "I just moved to Berlin last month."),
    ("assistant", "That's exciting! How are you finding the city?"),
    ("user", "I love it. I'm a software engineer at a startup here."),
    ("assistant", "Berlin has a great tech scene. What stack do you use?"),
    ("user", "Mostly Python and TypeScript. I prefer VS Code."),
    ("assistant", "Solid choices!"),
])

SAMPLE_LLM_RESPONSE = json.dumps([
    {"content": "User recently moved to Berlin", "category": "biographical", "confidence": 0.95},
    {"content": "User is a software engineer at a startup", "category": "biographical", "confidence": 0.9},
    {"content": "User works with Python and TypeScript", "category": "technical", "confidence": 0.95},
    {"content": "User prefers VS Code", "category": "preference", "confidence": 0.85},
])


# ===========================================================================
class TestExtractFacts:
    """Core extraction tests."""

    @pytest.mark.asyncio
    async def test_basic_extraction(self):
        llm = AsyncMock(return_value=SAMPLE_LLM_RESPONSE)

        facts = await extract_facts(SAMPLE_CONVERSATION, llm_call=llm)

        assert len(facts) == 4
        assert all("content" in f for f in facts)
        assert all("category" in f for f in facts)
        assert all("confidence" in f for f in facts)

    @pytest.mark.asyncio
    async def test_llm_receives_system_prompt(self):
        llm = AsyncMock(return_value="[]")

        await extract_facts(SAMPLE_CONVERSATION, llm_call=llm)

        llm.assert_called_once()
        prompt = llm.call_args[0][0]
        # The system prompt should contain extraction instructions
        assert "extract" in prompt.lower() or "fact" in prompt.lower()

    @pytest.mark.asyncio
    async def test_conversation_included_in_prompt(self):
        llm = AsyncMock(return_value="[]")

        await extract_facts(SAMPLE_CONVERSATION, llm_call=llm)

        prompt = llm.call_args[0][0]
        assert "Berlin" in prompt
        assert "Python" in prompt

    @pytest.mark.asyncio
    async def test_empty_conversation_returns_no_facts(self):
        llm = AsyncMock(return_value="[]")

        facts = await extract_facts([], llm_call=llm)

        assert facts == []
        llm.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_user_messages_returns_no_facts(self):
        msgs = _msgs([
            ("assistant", "Hello! How can I help?"),
            ("assistant", "Let me know if you need anything."),
        ])
        llm = AsyncMock(return_value="[]")

        facts = await extract_facts(msgs, llm_call=llm)

        assert facts == []
        llm.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_returns_no_facts(self):
        llm = AsyncMock(return_value="[]")

        facts = await extract_facts(SAMPLE_CONVERSATION, llm_call=llm)

        assert facts == []

    @pytest.mark.asyncio
    async def test_categories_are_validated(self):
        bad_response = json.dumps([
            {"content": "User likes cats", "category": "invalid_cat", "confidence": 0.8},
            {"content": "User lives in Berlin", "category": "biographical", "confidence": 0.9},
        ])
        llm = AsyncMock(return_value=bad_response)

        facts = await extract_facts(SAMPLE_CONVERSATION, llm_call=llm)

        # Invalid category should be filtered out
        assert len(facts) == 1
        assert facts[0]["category"] == "biographical"

    @pytest.mark.asyncio
    async def test_confidence_must_be_in_range(self):
        bad_response = json.dumps([
            {"content": "fact1", "category": "biographical", "confidence": 1.5},
            {"content": "fact2", "category": "biographical", "confidence": -0.1},
            {"content": "fact3", "category": "biographical", "confidence": 0.8},
        ])
        llm = AsyncMock(return_value=bad_response)

        facts = await extract_facts(SAMPLE_CONVERSATION, llm_call=llm)

        assert len(facts) == 1
        assert facts[0]["content"] == "fact3"

    @pytest.mark.asyncio
    async def test_missing_fields_filtered_out(self):
        bad_response = json.dumps([
            {"content": "good fact", "category": "biographical", "confidence": 0.8},
            {"category": "preference", "confidence": 0.7},  # missing content
            {"content": "no cat", "confidence": 0.7},  # missing category
        ])
        llm = AsyncMock(return_value=bad_response)

        facts = await extract_facts(SAMPLE_CONVERSATION, llm_call=llm)

        assert len(facts) == 1
        assert facts[0]["content"] == "good fact"


# ===========================================================================
class TestDeduplication:
    """Dedup against existing memories."""

    @pytest.mark.asyncio
    async def test_duplicate_facts_filtered(self):
        llm = AsyncMock(return_value=json.dumps([
            {"content": "User lives in Berlin", "category": "biographical", "confidence": 0.9},
            {"content": "User uses Python", "category": "technical", "confidence": 0.9},
        ]))
        existing = ["User recently moved to Berlin"]

        facts = await extract_facts(
            SAMPLE_CONVERSATION, llm_call=llm, existing_memories=existing,
        )

        # "User lives in Berlin" is semantically similar to existing — still
        # returned but marked duplicate so caller can decide.  The extractor
        # adds a `is_new` flag.
        berlin_fact = [f for f in facts if "Berlin" in f["content"]][0]
        python_fact = [f for f in facts if "Python" in f["content"]][0]
        assert berlin_fact["is_new"] is False
        assert python_fact["is_new"] is True

    @pytest.mark.asyncio
    async def test_no_existing_memories_all_new(self):
        llm = AsyncMock(return_value=SAMPLE_LLM_RESPONSE)

        facts = await extract_facts(
            SAMPLE_CONVERSATION, llm_call=llm, existing_memories=[],
        )

        assert all(f["is_new"] for f in facts)

    @pytest.mark.asyncio
    async def test_existing_memories_none_treated_as_empty(self):
        llm = AsyncMock(return_value=SAMPLE_LLM_RESPONSE)

        facts = await extract_facts(
            SAMPLE_CONVERSATION, llm_call=llm, existing_memories=None,
        )

        assert all(f["is_new"] for f in facts)


# ===========================================================================
class TestEdgeCases:
    """Robustness & error handling."""

    @pytest.mark.asyncio
    async def test_llm_returns_invalid_json(self):
        llm = AsyncMock(return_value="not json at all")

        facts = await extract_facts(SAMPLE_CONVERSATION, llm_call=llm)

        assert facts == []

    @pytest.mark.asyncio
    async def test_llm_returns_json_but_not_list(self):
        llm = AsyncMock(return_value='{"content": "fact"}')

        facts = await extract_facts(SAMPLE_CONVERSATION, llm_call=llm)

        assert facts == []

    @pytest.mark.asyncio
    async def test_llm_raises_exception(self):
        llm = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

        facts = await extract_facts(SAMPLE_CONVERSATION, llm_call=llm)

        assert facts == []

    @pytest.mark.asyncio
    async def test_llm_timeout(self):
        llm = AsyncMock(side_effect=TimeoutError("timeout"))

        facts = await extract_facts(SAMPLE_CONVERSATION, llm_call=llm)

        assert facts == []

    @pytest.mark.asyncio
    async def test_system_prompt_constant_exists(self):
        assert isinstance(FACT_EXTRACTION_PROMPT, str)
        assert len(FACT_EXTRACTION_PROMPT) > 50

    @pytest.mark.asyncio
    async def test_valid_categories_defined(self):
        assert isinstance(VALID_CATEGORIES, (set, frozenset, list, tuple))
        assert "biographical" in VALID_CATEGORIES
        assert "preference" in VALID_CATEGORIES
        assert "technical" in VALID_CATEGORIES


# ===========================================================================
class TestPromptContent:
    """Verify the extraction prompt has required elements."""

    def test_prompt_requests_json(self):
        assert "json" in FACT_EXTRACTION_PROMPT.lower() or "JSON" in FACT_EXTRACTION_PROMPT

    def test_prompt_mentions_categories(self):
        for cat in VALID_CATEGORIES:
            assert cat in FACT_EXTRACTION_PROMPT

    def test_prompt_mentions_confidence(self):
        assert "confidence" in FACT_EXTRACTION_PROMPT.lower()
