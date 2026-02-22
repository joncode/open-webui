"""Memory injection into system prompts — Phase 4.1

Retrieves relevant user memories and formats them for inclusion
in the LLM system prompt so the assistant has user context.
"""

import logging
from typing import Callable, Optional

log = logging.getLogger(__name__)

MEMORY_PREAMBLE = (
    "Here is what you know about this user from previous conversations:"
)

_DEFAULT_MAX_MEMORIES = 20


def format_memories_for_prompt(
    memories: Optional[list[dict]],
    max_memories: int = _DEFAULT_MAX_MEMORIES,
) -> str:
    """Format a list of memory dicts into a system-prompt block.

    Args:
        memories: List of dicts with at least a "content" key.
        max_memories: Maximum number of memories to include.

    Returns:
        Formatted string with preamble + bullet list, or "" if no memories.
    """
    if not memories:
        return ""

    truncated = memories[:max_memories]
    lines = [MEMORY_PREAMBLE, ""]
    for mem in truncated:
        content = mem.get("content", "") if isinstance(mem, dict) else str(mem)
        lines.append(f"- {content}")

    return "\n".join(lines)


async def build_memory_context(
    user_id: str,
    conversation_text: str,
    query_fn: Callable,
    max_memories: int = _DEFAULT_MAX_MEMORIES,
) -> str:
    """Query relevant memories and format for system prompt injection.

    Args:
        user_id: The user whose memories to retrieve.
        conversation_text: Recent conversation text for relevance matching.
        query_fn: Async callable(user_id, query_text) → list[dict].
        max_memories: Maximum memories to include.

    Returns:
        Formatted memory block string, or "" on error/no memories.
    """
    try:
        memories = await query_fn(user_id, conversation_text)
    except Exception:
        log.warning("memory_injector: query failed", exc_info=True)
        return ""

    return format_memories_for_prompt(memories, max_memories=max_memories)
