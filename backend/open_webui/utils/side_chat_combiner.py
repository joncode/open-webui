"""
Side chat combine logic for Jaco.

When a user opens a side chat on a step and then clicks "Combine",
this module handles merging the side chat discussion back into the
main chat by rewriting the original step.
"""

import logging
from typing import Optional

log = logging.getLogger(__name__)

COMBINE_SYSTEM_PROMPT = """You are rewriting a step in a multi-step guide based on a side discussion.

Original step:
{original_step}

Side discussion:
{side_chat_history}

Rewrite the original step incorporating the insights from the side discussion.
Keep it concise and actionable — this is still just one step in a larger plan.
If the side discussion fundamentally changes the approach, note that briefly.
Output ONLY the rewritten step text. No preamble."""


async def generate_combined_step(
    original_step_content: str,
    side_chat_messages: list[dict],
    llm_call=None,
) -> Optional[str]:
    """
    Generate a rewritten step incorporating side chat discussion.

    Args:
        original_step_content: The original step text
        side_chat_messages: List of {"role": str, "content": str} from side chat
        llm_call: Async function to call LLM. Signature: async (prompt: str) -> str

    Returns:
        Rewritten step content, or None if generation fails
    """
    if not llm_call:
        log.warning("No LLM call function provided for combine")
        return None

    # Format side chat history
    history_lines = []
    for msg in side_chat_messages:
        role = "User" if msg["role"] == "user" else "Jaco"
        history_lines.append(f"{role}: {msg['content']}")

    side_chat_history = "\n".join(history_lines)

    prompt = COMBINE_SYSTEM_PROMPT.format(
        original_step=original_step_content,
        side_chat_history=side_chat_history,
    )

    try:
        result = await llm_call(prompt)
        return result.strip()
    except Exception as e:
        log.error(f"Failed to generate combined step: {e}")
        return None
