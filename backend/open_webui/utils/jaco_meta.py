"""
Jaco-specific metadata helpers for the chat meta JSON field.

Instead of adding new columns (which would require Alembic migrations),
we store Jaco-specific data in the existing chat.meta JSON field:

chat.meta = {
    ...existing Open WebUI meta...,
    "jaco": {
        "step_context": { ... },
        "parent_chat_id": "...",
        "split_summary": "...",
        "topic_summary": "...",
        "side_chat_active": false
    }
}
"""

from typing import Optional
from open_webui.utils.step_mode import StepContext


def get_jaco_meta(meta: Optional[dict]) -> dict:
    """Extract Jaco-specific metadata from chat meta, with defaults."""
    if not meta:
        return _default_jaco_meta()
    return meta.get("jaco", _default_jaco_meta())


def set_jaco_meta(meta: Optional[dict], jaco_data: dict) -> dict:
    """Set Jaco-specific metadata on chat meta."""
    if not meta:
        meta = {}
    meta["jaco"] = jaco_data
    return meta


def get_step_context(meta: Optional[dict]) -> StepContext:
    """Get step context from chat meta."""
    jaco = get_jaco_meta(meta)
    return StepContext.from_dict(jaco.get("step_context"))


def set_step_context(meta: Optional[dict], step_ctx: StepContext) -> dict:
    """Update step context in chat meta."""
    jaco = get_jaco_meta(meta)
    jaco["step_context"] = step_ctx.to_dict()
    return set_jaco_meta(meta, jaco)


def get_parent_chat_id(meta: Optional[dict]) -> Optional[str]:
    """Get parent chat ID (for topic-split lineage)."""
    return get_jaco_meta(meta).get("parent_chat_id")


def set_parent_chat_id(meta: Optional[dict], parent_id: str) -> dict:
    """Set parent chat ID after a topic split."""
    jaco = get_jaco_meta(meta)
    jaco["parent_chat_id"] = parent_id
    return set_jaco_meta(meta, jaco)


def get_split_summary(meta: Optional[dict]) -> Optional[str]:
    """Get the context summary injected after a topic split."""
    return get_jaco_meta(meta).get("split_summary")


def set_split_summary(meta: Optional[dict], summary: str) -> dict:
    """Set context summary after a topic split."""
    jaco = get_jaco_meta(meta)
    jaco["split_summary"] = summary
    return set_jaco_meta(meta, jaco)


def _default_jaco_meta() -> dict:
    return {
        "step_context": StepContext().to_dict(),
        "parent_chat_id": None,
        "split_summary": None,
        "topic_summary": None,
        "side_chat_active": False,
    }
