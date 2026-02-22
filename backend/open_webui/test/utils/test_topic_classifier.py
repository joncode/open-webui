import math
import pytest
from unittest.mock import AsyncMock

from open_webui.utils.topic_classifier import (
    TopicConfig,
    SplitDecision,
    cosine_similarity,
    compute_running_topic_embedding,
    classify_topic_shift,
    LLM_CONFIRMATION_PROMPT,
)


class TestCoseSimilarity:
    """Tests for cosine_similarity math correctness."""

    def test_identical_vectors(self):
        a = [1.0, 2.0, 3.0]
        assert cosine_similarity(a, a) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_known_value(self):
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        dot = 1 * 4 + 2 * 5 + 3 * 6  # 32
        norm_a = math.sqrt(1 + 4 + 9)  # sqrt(14)
        norm_b = math.sqrt(16 + 25 + 36)  # sqrt(77)
        expected = dot / (norm_a * norm_b)
        assert cosine_similarity(a, b) == pytest.approx(expected)

    def test_empty_vectors(self):
        assert cosine_similarity([], []) == 0.0

    def test_different_lengths(self):
        assert cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0]) == 0.0

    def test_zero_vector_a(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0

    def test_zero_vector_b(self):
        assert cosine_similarity([1.0, 2.0], [0.0, 0.0]) == 0.0

    def test_both_zero_vectors(self):
        assert cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0

    def test_unit_vectors(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_negative_values(self):
        a = [-1.0, -2.0]
        b = [-3.0, -4.0]
        # Both point in same general direction (third quadrant)
        assert cosine_similarity(a, b) > 0.9

    def test_single_dimension(self):
        assert cosine_similarity([5.0], [3.0]) == pytest.approx(1.0)
        assert cosine_similarity([5.0], [-3.0]) == pytest.approx(-1.0)


class TestComputeRunningTopicEmbedding:
    """Tests for compute_running_topic_embedding with decay."""

    def test_empty_embeddings(self):
        assert compute_running_topic_embedding([]) is None

    def test_single_embedding(self):
        emb = [1.0, 2.0, 3.0]
        result = compute_running_topic_embedding([emb])
        # With one embedding, weight is decay^0 = 1, so result == emb
        assert result == pytest.approx(emb)

    def test_two_embeddings_decay(self):
        emb1 = [1.0, 0.0]  # older
        emb2 = [0.0, 1.0]  # most recent
        decay = 0.5
        result = compute_running_topic_embedding([emb1, emb2], decay=decay)

        # After reverse: [emb2, emb1]
        # emb2 weight = 0.5^0 = 1.0
        # emb1 weight = 0.5^1 = 0.5
        # total weight = 1.5
        # dim0 = (1.0 * 0.0 + 0.5 * 1.0) / 1.5 = 0.5/1.5 = 1/3
        # dim1 = (1.0 * 1.0 + 0.5 * 0.0) / 1.5 = 1.0/1.5 = 2/3
        assert result[0] == pytest.approx(1 / 3)
        assert result[1] == pytest.approx(2 / 3)

    def test_window_limits_embeddings(self):
        embeddings = [[float(i)] for i in range(10)]
        result = compute_running_topic_embedding(embeddings, window=3)
        # Should only use last 3: [7], [8], [9]
        # After reverse: [9], [8], [7]
        # weights: 1.0, 0.8, 0.64
        # total = 2.44
        # result = (1.0*9 + 0.8*8 + 0.64*7) / 2.44
        expected = (9.0 + 6.4 + 4.48) / 2.44
        assert result[0] == pytest.approx(expected)

    def test_decay_zero_only_most_recent(self):
        # decay=0 means only the most recent has nonzero weight (0^0 = 1, 0^i = 0 for i>0)
        emb1 = [10.0, 20.0]
        emb2 = [1.0, 2.0]
        result = compute_running_topic_embedding([emb1, emb2], decay=0.0)
        # Only emb2 matters (most recent, weight=1), others weight=0
        # total weight = 1.0 + 0.0 = 1.0
        assert result == pytest.approx([1.0, 2.0])

    def test_decay_one_equal_weight(self):
        emb1 = [2.0, 0.0]
        emb2 = [0.0, 4.0]
        result = compute_running_topic_embedding([emb1, emb2], decay=1.0)
        # Both have weight 1^i = 1, so it's a straight average
        assert result == pytest.approx([1.0, 2.0])

    def test_preserves_dimensionality(self):
        emb = [[1.0, 2.0, 3.0, 4.0, 5.0]]
        result = compute_running_topic_embedding(emb)
        assert len(result) == 5

    def test_default_params(self):
        emb = [[1.0, 2.0]]
        result = compute_running_topic_embedding(emb)
        assert result is not None


class TestTopicConfig:
    """Tests for TopicConfig defaults."""

    def test_defaults(self):
        config = TopicConfig()
        assert config.similarity_threshold == 0.65
        assert config.min_messages_before_split == 3
        assert config.embedding_window == 5
        assert config.embedding_decay == 0.8
        assert config.use_llm_confirmation is True
        assert config.auto_title_on_split is True
        assert config.split_timeout_ms == 5000


class TestSplitDecision:
    """Tests for SplitDecision defaults."""

    def test_defaults(self):
        d = SplitDecision()
        assert d.should_split is False
        assert d.new_topic_name == ""
        assert d.confidence == 0.0
        assert d.similarity_score == 1.0
        assert d.llm_confirmed is None


class TestClassifyTopicShift:
    """Tests for classify_topic_shift async function."""

    @pytest.mark.asyncio
    async def test_too_few_messages_no_split(self):
        config = TopicConfig(min_messages_before_split=3)
        result = await classify_topic_shift(
            new_message="Hello",
            new_embedding=[1.0, 0.0],
            chat_message_embeddings=[[1.0, 0.0]],
            chat_topic_summary="Greetings",
            config=config,
            message_count=2,
        )
        assert result.should_split is False

    @pytest.mark.asyncio
    async def test_high_similarity_no_split(self):
        # Same vector -> similarity=1.0, above threshold
        emb = [1.0, 0.0, 0.0]
        config = TopicConfig(similarity_threshold=0.65, use_llm_confirmation=False)
        result = await classify_topic_shift(
            new_message="More about the same topic",
            new_embedding=emb,
            chat_message_embeddings=[emb, emb, emb],
            chat_topic_summary="Our topic",
            config=config,
            message_count=5,
        )
        assert result.should_split is False
        assert result.similarity_score == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_low_similarity_no_llm_triggers_split(self):
        # Orthogonal vectors -> similarity=0.0, well below threshold
        config = TopicConfig(
            similarity_threshold=0.65,
            use_llm_confirmation=False,
        )
        result = await classify_topic_shift(
            new_message="Completely different topic",
            new_embedding=[0.0, 1.0],
            chat_message_embeddings=[[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]],
            chat_topic_summary="Original topic",
            config=config,
            message_count=5,
        )
        assert result.should_split is True
        assert result.new_topic_name == "New Topic"
        assert result.confidence == pytest.approx(1.0)
        assert result.llm_confirmed is None

    @pytest.mark.asyncio
    async def test_low_similarity_llm_confirms_new(self):
        mock_llm = AsyncMock(return_value="NEW: Machine Learning Basics")
        config = TopicConfig(
            similarity_threshold=0.65,
            use_llm_confirmation=True,
        )
        result = await classify_topic_shift(
            new_message="Tell me about neural networks",
            new_embedding=[0.0, 1.0],
            chat_message_embeddings=[[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]],
            chat_topic_summary="Cooking recipes",
            config=config,
            message_count=5,
            llm_call=mock_llm,
        )
        assert result.should_split is True
        assert result.new_topic_name == "Machine Learning Basics"
        assert result.llm_confirmed is True
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_low_similarity_llm_says_same(self):
        mock_llm = AsyncMock(return_value="SAME")
        config = TopicConfig(
            similarity_threshold=0.65,
            use_llm_confirmation=True,
        )
        result = await classify_topic_shift(
            new_message="What about the sauce?",
            new_embedding=[0.0, 1.0],
            chat_message_embeddings=[[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]],
            chat_topic_summary="Cooking recipes",
            config=config,
            message_count=5,
            llm_call=mock_llm,
        )
        assert result.should_split is False
        assert result.llm_confirmed is False

    @pytest.mark.asyncio
    async def test_llm_exception_falls_through_to_split(self):
        mock_llm = AsyncMock(side_effect=RuntimeError("LLM down"))
        config = TopicConfig(
            similarity_threshold=0.65,
            use_llm_confirmation=True,
        )
        result = await classify_topic_shift(
            new_message="Something new",
            new_embedding=[0.0, 1.0],
            chat_message_embeddings=[[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]],
            chat_topic_summary="Old topic",
            config=config,
            message_count=5,
            llm_call=mock_llm,
        )
        assert result.should_split is True
        assert result.new_topic_name == "New Topic"

    @pytest.mark.asyncio
    async def test_empty_embeddings_no_split(self):
        config = TopicConfig()
        result = await classify_topic_shift(
            new_message="Hello",
            new_embedding=[1.0, 0.0],
            chat_message_embeddings=[],
            chat_topic_summary="",
            config=config,
            message_count=5,
        )
        assert result.should_split is False

    @pytest.mark.asyncio
    async def test_llm_prompt_format(self):
        """Verify the LLM is called with the correct prompt format."""
        mock_llm = AsyncMock(return_value="SAME")
        config = TopicConfig(
            similarity_threshold=0.65,
            use_llm_confirmation=True,
        )
        await classify_topic_shift(
            new_message="What about cats?",
            new_embedding=[0.0, 1.0],
            chat_message_embeddings=[[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]],
            chat_topic_summary="Dogs are great",
            config=config,
            message_count=5,
            llm_call=mock_llm,
        )
        call_args = mock_llm.call_args[0][0]
        assert "Dogs are great" in call_args
        assert "What about cats?" in call_args

    @pytest.mark.asyncio
    async def test_use_llm_confirmation_true_but_no_llm_call(self):
        """If use_llm_confirmation is True but no llm_call provided, fall through to embedding-only."""
        config = TopicConfig(
            similarity_threshold=0.65,
            use_llm_confirmation=True,
        )
        result = await classify_topic_shift(
            new_message="New topic",
            new_embedding=[0.0, 1.0],
            chat_message_embeddings=[[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]],
            chat_topic_summary="Old topic",
            config=config,
            message_count=5,
            llm_call=None,
        )
        assert result.should_split is True
        assert result.new_topic_name == "New Topic"

    @pytest.mark.asyncio
    async def test_confidence_is_one_minus_similarity(self):
        """Confidence should be 1.0 - similarity_score when split is triggered."""
        config = TopicConfig(
            similarity_threshold=0.65,
            use_llm_confirmation=False,
        )
        # Create vectors with known similarity
        a = [1.0, 0.0]
        b = [0.6, 0.8]  # similarity with [1,0] = 0.6 (below 0.65 threshold)
        result = await classify_topic_shift(
            new_message="New",
            new_embedding=b,
            chat_message_embeddings=[a, a, a],
            chat_topic_summary="Old",
            config=config,
            message_count=5,
        )
        expected_sim = cosine_similarity(b, a)  # a is topic emb since all same
        assert result.should_split is True
        assert result.confidence == pytest.approx(1.0 - expected_sim)

    @pytest.mark.asyncio
    async def test_exactly_at_threshold_no_split(self):
        """Similarity exactly at threshold should NOT trigger split."""
        config = TopicConfig(
            similarity_threshold=1.0,  # Set threshold to exactly 1.0
            use_llm_confirmation=False,
        )
        emb = [1.0, 0.0]
        result = await classify_topic_shift(
            new_message="Same",
            new_embedding=emb,
            chat_message_embeddings=[emb, emb, emb],
            chat_topic_summary="Topic",
            config=config,
            message_count=5,
        )
        assert result.should_split is False
