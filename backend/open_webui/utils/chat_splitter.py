"""
Chat splitting logic for Jaco's auto-topic-split feature.

When the topic classifier detects a topic shift, this module handles:
1. Generating a context summary of the original conversation
2. Building a new chat with the triggering message
3. Auto-titling both the original and new chats via LLM
4. Recording the split boundary for UI navigation
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class SplitConfig:
    """Configuration for chat splitting behavior."""

    auto_title: bool = True
    include_context_summary: bool = True
    max_context_messages: int = 10
    context_summary_max_tokens: int = 200


@dataclass
class SplitResult:
    """Result of a chat split operation."""

    success: bool = False
    new_chat_id: str = ""
    new_chat_title: str = ""
    original_chat_new_title: str = ""
    context_summary: str = ""
    error: Optional[str] = None


@dataclass
class TopicBoundary:
    """Records a topic split boundary between two chats."""

    original_chat_id: str
    new_chat_id: str
    triggering_message: str
    old_topic: str
    new_topic: str
    split_timestamp: float = field(default_factory=time.time)
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "original_chat_id": self.original_chat_id,
            "new_chat_id": self.new_chat_id,
            "triggering_message": self.triggering_message,
            "old_topic": self.old_topic,
            "new_topic": self.new_topic,
            "split_timestamp": self.split_timestamp,
            "confidence": self.confidence,
        }


CONTEXT_SUMMARY_PROMPT = """Summarize the following conversation in 1-2 sentences.
Focus on the key topic and any important context that would help continue the conversation.

Conversation:
{conversation}

Summary:"""


TITLE_GENERATION_PROMPT = """Generate a concise chat title (3-6 words) for a conversation about:
Topic: {topic_hint}
Latest message: "{message}"

Respond with ONLY the title, no quotes or punctuation."""


async def generate_context_summary(
    messages: list[dict],
    llm_call=None,
    max_messages: int = 10,
) -> str:
    """Generate a brief summary of the conversation for context carry-over."""
    if not messages:
        return ""

    if not llm_call:
        return ""

    recent = messages[-max_messages:]
    lines = []
    for msg in recent:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")

    conversation = "\n".join(lines)
    prompt = CONTEXT_SUMMARY_PROMPT.format(conversation=conversation)

    try:
        result = await llm_call(prompt)
        return result.strip()
    except Exception as e:
        log.warning(f"Context summary generation failed: {e}")
        return ""


async def generate_chat_title(
    topic_hint: str,
    recent_message: str,
    llm_call=None,
) -> str:
    """Generate a chat title via LLM, falling back to topic_hint."""
    fallback = topic_hint if topic_hint else "New Chat"

    if not llm_call:
        return fallback

    prompt = TITLE_GENERATION_PROMPT.format(
        topic_hint=topic_hint,
        message=recent_message,
    )

    try:
        result = await llm_call(prompt)
        return result.strip()
    except Exception as e:
        log.warning(f"Title generation failed: {e}")
        return fallback


def build_new_chat_data(
    user_id: str,
    title: str,
    triggering_message: dict,
    context_summary: str,
    parent_chat_id: str,
) -> dict:
    """Build the data dict for creating a new split chat."""
    chat_id = str(uuid.uuid4())
    now = int(time.time())

    messages = []

    # Add context summary as system message if available
    if context_summary:
        messages.append(
            {
                "role": "system",
                "content": f"Context from previous conversation: {context_summary}",
            }
        )

    messages.append(triggering_message)

    return {
        "id": chat_id,
        "user_id": user_id,
        "title": title,
        "chat": {"messages": messages},
        "created_at": now,
        "updated_at": now,
        "parent_chat_id": parent_chat_id,
        "split_summary": context_summary,
    }


def record_topic_boundary(
    original_chat_id: str,
    new_chat_id: str,
    triggering_message: str,
    old_topic: str,
    new_topic: str,
    confidence: float = 0.0,
) -> TopicBoundary:
    """Create a TopicBoundary record for the split."""
    return TopicBoundary(
        original_chat_id=original_chat_id,
        new_chat_id=new_chat_id,
        triggering_message=triggering_message,
        old_topic=old_topic,
        new_topic=new_topic,
        confidence=confidence,
    )


async def execute_chat_split(
    original_chat_id: str,
    user_id: str,
    messages: list[dict],
    triggering_message: dict,
    new_topic_name: str,
    old_topic_name: str,
    confidence: float = 0.0,
    llm_call=None,
    config: SplitConfig = None,
) -> SplitResult:
    """
    Orchestrate a full chat split.

    1. Generate context summary (if configured)
    2. Generate titles for both chats (if auto_title)
    3. Build new chat data
    4. Record topic boundary
    5. Return SplitResult
    """
    if config is None:
        config = SplitConfig()

    result = SplitResult()

    # Step 1: Context summary
    context_summary = ""
    if config.include_context_summary:
        context_summary = await generate_context_summary(
            messages,
            llm_call=llm_call,
            max_messages=config.max_context_messages,
        )

    # Step 2: Generate titles
    if config.auto_title and llm_call:
        new_title = await generate_chat_title(
            topic_hint=new_topic_name,
            recent_message=triggering_message.get("content", ""),
            llm_call=llm_call,
        )
        original_title = await generate_chat_title(
            topic_hint=old_topic_name,
            recent_message=messages[-1].get("content", "") if messages else "",
            llm_call=llm_call,
        )
    else:
        new_title = new_topic_name if new_topic_name else "New Chat"
        original_title = old_topic_name if old_topic_name else "Previous Chat"

    # Step 3: Build new chat
    new_chat = build_new_chat_data(
        user_id=user_id,
        title=new_title,
        triggering_message=triggering_message,
        context_summary=context_summary,
        parent_chat_id=original_chat_id,
    )

    # Step 4: Record boundary
    record_topic_boundary(
        original_chat_id=original_chat_id,
        new_chat_id=new_chat["id"],
        triggering_message=triggering_message.get("content", ""),
        old_topic=old_topic_name,
        new_topic=new_topic_name,
        confidence=confidence,
    )

    # Step 5: Populate result
    result.success = True
    result.new_chat_id = new_chat["id"]
    result.new_chat_title = new_title
    result.original_chat_new_title = original_title
    result.context_summary = context_summary

    return result
