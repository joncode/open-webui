"""
Topic classification for Jaco's auto-topic-split feature.

Two-stage detection:
1. Fast path: cosine similarity of message embedding vs running topic embedding
2. Confirmation: lightweight LLM call to verify topic shift

When a shift is confirmed, Jaco shows a 5-second alert banner before splitting.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class TopicConfig:
    """Tunable parameters for topic classification."""
    similarity_threshold: float = 0.65
    min_messages_before_split: int = 3
    embedding_window: int = 5
    embedding_decay: float = 0.8
    use_llm_confirmation: bool = True
    auto_title_on_split: bool = True
    split_timeout_ms: int = 5000


@dataclass
class SplitDecision:
    """Result of topic classification."""
    should_split: bool = False
    new_topic_name: str = ""
    confidence: float = 0.0
    similarity_score: float = 1.0
    llm_confirmed: Optional[bool] = None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b) or len(a) == 0:
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def compute_running_topic_embedding(
    message_embeddings: list[list[float]],
    decay: float = 0.8,
    window: int = 5,
) -> Optional[list[float]]:
    """
    Compute a weighted average of recent message embeddings.

    topic_embedding = Σ (decay^i * embedding_i) / Σ (decay^i)

    Where i=0 is the most recent message. This gives a "what is this
    chat about right now" vector that naturally drifts as conversation
    evolves.
    """
    if not message_embeddings:
        return None

    recent = message_embeddings[-window:]
    recent.reverse()  # Most recent first

    dim = len(recent[0])
    weighted_sum = [0.0] * dim
    weight_total = 0.0

    for i, emb in enumerate(recent):
        w = decay ** i
        weight_total += w
        for d in range(dim):
            weighted_sum[d] += w * emb[d]

    if weight_total == 0:
        return None

    return [x / weight_total for x in weighted_sum]


LLM_CONFIRMATION_PROMPT = """Given the current conversation topic: "{topic_summary}"

The user just said: "{new_message}"

Is this a continuation of the current topic, or a shift to a new topic?
Respond with exactly one of:
SAME
NEW: [brief topic name, 3-5 words]"""


async def classify_topic_shift(
    new_message: str,
    new_embedding: list[float],
    chat_message_embeddings: list[list[float]],
    chat_topic_summary: str,
    config: TopicConfig,
    message_count: int,
    llm_call=None,
) -> SplitDecision:
    """
    Determine if a new message represents a topic shift.

    Args:
        new_message: The user's latest message text
        new_embedding: Embedding vector of the new message
        chat_message_embeddings: Recent message embeddings for the chat
        chat_topic_summary: Brief summary of the current chat topic
        config: Topic classification config
        message_count: Total messages in the chat so far
        llm_call: Async function to call LLM for confirmation.
                  Signature: async (prompt: str) -> str
    """
    decision = SplitDecision()

    # Don't split too early
    if message_count < config.min_messages_before_split:
        return decision

    # Stage 1: Embedding similarity
    topic_embedding = compute_running_topic_embedding(
        chat_message_embeddings,
        decay=config.embedding_decay,
        window=config.embedding_window,
    )

    if topic_embedding is None:
        return decision

    similarity = cosine_similarity(new_embedding, topic_embedding)
    decision.similarity_score = similarity

    log.debug(
        f"Topic similarity: {similarity:.3f} (threshold: {config.similarity_threshold})"
    )

    if similarity >= config.similarity_threshold:
        # Similar enough — no split
        return decision

    # Stage 2: LLM confirmation
    if config.use_llm_confirmation and llm_call:
        prompt = LLM_CONFIRMATION_PROMPT.format(
            topic_summary=chat_topic_summary,
            new_message=new_message,
        )
        try:
            response = await llm_call(prompt)
            response = response.strip()

            if response.upper().startswith("NEW:"):
                decision.should_split = True
                decision.new_topic_name = response[4:].strip()
                decision.llm_confirmed = True
                decision.confidence = 1.0 - similarity
            else:
                decision.llm_confirmed = False
                log.debug("LLM says SAME topic despite low similarity")

        except Exception as e:
            log.warning(f"LLM confirmation failed: {e}")
            # Fall through to embedding-only decision
            decision.should_split = True
            decision.new_topic_name = "New Topic"
            decision.confidence = 1.0 - similarity
    else:
        # No LLM confirmation — use embedding similarity alone
        decision.should_split = True
        decision.new_topic_name = "New Topic"
        decision.confidence = 1.0 - similarity

    return decision
