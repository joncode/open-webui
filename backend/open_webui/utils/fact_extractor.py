"""Fact extraction from conversation messages — Phase 4.1

After each assistant response, call extract_facts() to pull out
personal facts about the user (biographical, preferences, technical, etc.).
"""

import json
import logging
from difflib import SequenceMatcher
from typing import Callable, Optional

log = logging.getLogger(__name__)

VALID_CATEGORIES = frozenset([
    "biographical",
    "preference",
    "technical",
    "behavioral",
    "contextual",
])

FACT_EXTRACTION_PROMPT = """\
You are a fact extraction engine.  Given a conversation between a user and \
an assistant, extract personal facts about the **user** only.

Return a JSON array of objects.  Each object must have exactly these keys:
- "content": a concise factual statement about the user (string)
- "category": one of: biographical, preference, technical, behavioral, contextual
- "confidence": a float between 0.0 and 1.0

Rules:
- Only extract facts the user explicitly stated or clearly implied.
- Do NOT invent, assume, or speculate.
- Do NOT extract facts about the assistant.
- If there are no extractable user facts, return an empty array [].
- Return ONLY the JSON array, no markdown, no commentary.

Categories:
- biographical: name, location, age, occupation, life events
- preference: likes, dislikes, tool/language/editor choices
- technical: programming languages, frameworks, skills, stack
- behavioral: work habits, communication style, schedule
- contextual: current project, immediate goals, recent events

Conversation:
{conversation}

JSON array of extracted facts:"""

_SIMILARITY_THRESHOLD = 0.65


def _has_user_messages(messages: list[dict]) -> bool:
    return any(m.get("role") == "user" for m in messages)


def _format_conversation(messages: list[dict]) -> str:
    lines = []
    for m in messages:
        role = m.get("role", "unknown").capitalize()
        content = m.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _validate_fact(fact: dict) -> bool:
    if not isinstance(fact, dict):
        return False
    if "content" not in fact or "category" not in fact or "confidence" not in fact:
        return False
    if fact["category"] not in VALID_CATEGORIES:
        return False
    try:
        conf = float(fact["confidence"])
    except (TypeError, ValueError):
        return False
    if conf < 0.0 or conf > 1.0:
        return False
    return True


def _is_duplicate(fact_content: str, existing: list[str]) -> bool:
    for mem in existing:
        ratio = SequenceMatcher(None, fact_content.lower(), mem.lower()).ratio()
        if ratio >= _SIMILARITY_THRESHOLD:
            return True
    return False


async def extract_facts(
    messages: list[dict],
    *,
    llm_call: Callable,
    existing_memories: Optional[list[str]] = None,
) -> list[dict]:
    """Extract user facts from conversation messages via LLM.

    Args:
        messages: List of {role, content} message dicts.
        llm_call: Async callable that takes a prompt string and returns text.
        existing_memories: Optional list of existing memory content strings
            for deduplication.

    Returns:
        List of fact dicts with keys: content, category, confidence, is_new.
        Returns [] on any error.
    """
    if not messages or not _has_user_messages(messages):
        return []

    existing = existing_memories or []

    conversation_text = _format_conversation(messages)
    prompt = FACT_EXTRACTION_PROMPT.format(conversation=conversation_text)

    try:
        raw = await llm_call(prompt)
    except Exception:
        log.warning("fact_extractor: LLM call failed", exc_info=True)
        return []

    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        log.warning("fact_extractor: LLM returned invalid JSON")
        return []

    if not isinstance(parsed, list):
        log.warning("fact_extractor: LLM returned non-list JSON")
        return []

    facts = []
    for item in parsed:
        if not _validate_fact(item):
            continue
        fact = {
            "content": item["content"],
            "category": item["category"],
            "confidence": float(item["confidence"]),
            "is_new": not _is_duplicate(item["content"], existing),
        }
        facts.append(fact)

    return facts
