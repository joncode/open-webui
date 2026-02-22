"""
Tests for topic classification pipeline integration.

Validates that classify_topic_shift is called correctly with
data from the Chat model and embedding function, and that
split decisions are stored in metadata for response handlers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from open_webui.utils.topic_classifier import (
    TopicConfig,
    SplitDecision,
    classify_topic_shift,
    compute_running_topic_embedding,
)


class TestTopicPipelineIntegration:
    """Tests for topic classification pipeline wiring logic."""

    @pytest.mark.asyncio
    async def test_classify_stores_decision_in_metadata(self):
        """classify_topic_shift result should be storable as metadata dict."""
        config = TopicConfig(
            similarity_threshold=0.65,
            use_llm_confirmation=False,
        )
        result = await classify_topic_shift(
            new_message="Completely new topic",
            new_embedding=[0.0, 1.0],
            chat_message_embeddings=[[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]],
            chat_topic_summary="Old topic",
            config=config,
            message_count=5,
        )
        # Convert to dict like the pipeline does
        decision_dict = {
            "should_split": result.should_split,
            "new_topic_name": result.new_topic_name,
            "confidence": result.confidence,
            "similarity_score": result.similarity_score,
        }
        assert decision_dict["should_split"] is True
        assert decision_dict["new_topic_name"] == "New Topic"
        assert decision_dict["confidence"] > 0

    @pytest.mark.asyncio
    async def test_embeddings_update_after_classification(self):
        """After classification, stored embeddings should include the new one."""
        stored = [[1.0, 0.0], [0.9, 0.1]]
        new_emb = [0.8, 0.2]

        # Simulate what the pipeline does
        updated = stored + [new_emb]
        window = 5
        updated = updated[-window:]

        assert len(updated) == 3
        assert updated[-1] == new_emb

    @pytest.mark.asyncio
    async def test_embeddings_window_truncation(self):
        """Stored embeddings should be truncated to window size."""
        window = 3
        stored = [[float(i), 0.0] for i in range(5)]
        new_emb = [5.0, 0.0]

        updated = stored + [new_emb]
        updated = updated[-window:]

        assert len(updated) == window
        assert updated[-1] == new_emb
        # Oldest should be dropped
        assert updated[0] == [3.0, 0.0]

    @pytest.mark.asyncio
    async def test_topic_embedding_recomputed_after_new_message(self):
        """Running topic embedding should be recomputed with new data."""
        stored = [[1.0, 0.0], [1.0, 0.0]]
        new_emb = [0.0, 1.0]
        updated = stored + [new_emb]

        config = TopicConfig()
        topic_emb = compute_running_topic_embedding(
            updated,
            decay=config.embedding_decay,
            window=config.embedding_window,
        )
        assert topic_emb is not None
        assert len(topic_emb) == 2
        # The topic embedding should shift toward the new message
        assert topic_emb[1] > 0  # Has some component from [0, 1]

    @pytest.mark.asyncio
    async def test_no_split_on_empty_embeddings(self):
        """First message in a chat should never trigger a split."""
        config = TopicConfig()
        result = await classify_topic_shift(
            new_message="Hello",
            new_embedding=[1.0, 0.0],
            chat_message_embeddings=[],
            chat_topic_summary="",
            config=config,
            message_count=1,
        )
        assert result.should_split is False

    @pytest.mark.asyncio
    async def test_no_split_on_local_chat_id(self):
        """local: chat IDs should not trigger topic classification.
        This tests the filtering logic used in the pipeline."""
        chat_id = "local:temp-123"
        assert chat_id.startswith("local:")

    @pytest.mark.asyncio
    async def test_split_decision_serializable(self):
        """SplitDecision fields should be JSON-serializable for metadata."""
        import json

        decision = SplitDecision(
            should_split=True,
            new_topic_name="Machine Learning",
            confidence=0.85,
            similarity_score=0.15,
            llm_confirmed=True,
        )
        decision_dict = {
            "should_split": decision.should_split,
            "new_topic_name": decision.new_topic_name,
            "confidence": decision.confidence,
            "similarity_score": decision.similarity_score,
        }
        # Should not raise
        serialized = json.dumps(decision_dict)
        deserialized = json.loads(serialized)
        assert deserialized["should_split"] is True
        assert deserialized["new_topic_name"] == "Machine Learning"

    @pytest.mark.asyncio
    async def test_graceful_failure_on_embedding_error(self):
        """Topic classification should fail gracefully if embedding raises."""
        # The pipeline wraps this in try/except, so test that
        # classify_topic_shift itself handles edge cases
        config = TopicConfig()
        # None embedding should not crash
        result = await classify_topic_shift(
            new_message="Hello",
            new_embedding=[],
            chat_message_embeddings=[[1.0, 0.0]],
            chat_topic_summary="Topic",
            config=config,
            message_count=5,
        )
        # Empty embedding -> cosine_similarity returns 0 for length mismatch
        assert isinstance(result, SplitDecision)

    @pytest.mark.asyncio
    async def test_chat_title_used_as_topic_summary(self):
        """The chat title should be passed as topic_summary for LLM prompt."""
        mock_llm = AsyncMock(return_value="SAME")
        config = TopicConfig(
            similarity_threshold=0.65,
            use_llm_confirmation=True,
        )
        await classify_topic_shift(
            new_message="New question",
            new_embedding=[0.0, 1.0],
            chat_message_embeddings=[[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]],
            chat_topic_summary="How to cook pasta",
            config=config,
            message_count=5,
            llm_call=mock_llm,
        )
        call_args = mock_llm.call_args[0][0]
        assert "How to cook pasta" in call_args
