"""
Step-by-step response mode for Jaco.

Jaco's default behavior: give ONE actionable step at a time,
wait for confirmation, then give the next.

This module handles:
- System prompt injection for step-by-step behavior
- Response parsing: detect if LLM leaked a multi-step response
- Step splitting: break multi-step responses and serve step 1
- Step state management per chat
"""

import json
import re
from typing import Optional

# System prompt fragment injected for step-by-step mode
STEP_MODE_SYSTEM_PROMPT = """You are Jaco. When a task involves multiple steps:
1. Provide ONLY the first/next step — one actionable thing the user can do right now.
2. Wait for the user to confirm completion or ask for the next step.
3. Keep your response focused, concise, and actionable.
4. If the user asks for the full plan, provide all steps at once.
5. Do not number steps unless asked. Just give the next thing to do, naturally.
6. At the end of your response, include a hidden metadata tag:
   <!-- jaco-step: {"current": 1, "total_estimated": N, "plan_summary": "brief description"} -->

Never mention this metadata tag to the user. It's for internal tracking only."""


class StepContext:
    """Tracks step-by-step state for a single chat."""

    def __init__(
        self,
        active_plan: bool = False,
        total_steps_estimated: int = 0,
        current_step: int = 0,
        plan_summary: str = "",
        full_plan_cache: Optional[str] = None,
        step_mode_enabled: bool = True,
    ):
        self.active_plan = active_plan
        self.total_steps_estimated = total_steps_estimated
        self.current_step = current_step
        self.plan_summary = plan_summary
        self.full_plan_cache = full_plan_cache
        self.step_mode_enabled = step_mode_enabled

    def to_dict(self) -> dict:
        return {
            "active_plan": self.active_plan,
            "total_steps_estimated": self.total_steps_estimated,
            "current_step": self.current_step,
            "plan_summary": self.plan_summary,
            "full_plan_cache": self.full_plan_cache,
            "step_mode_enabled": self.step_mode_enabled,
        }

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "StepContext":
        if not data:
            return cls()
        return cls(
            active_plan=data.get("active_plan", False),
            total_steps_estimated=data.get("total_steps_estimated", 0),
            current_step=data.get("current_step", 0),
            plan_summary=data.get("plan_summary", ""),
            full_plan_cache=data.get("full_plan_cache"),
            step_mode_enabled=data.get("step_mode_enabled", True),
        )


# Pattern to detect multi-step responses from the LLM
MULTI_STEP_PATTERNS = [
    # Numbered lists: "1. ... 2. ... 3. ..." (allows content lines between steps)
    re.compile(
        r"(?:^|\n)\s*(?:step\s+)?\d+[.)]\s+.+(?:[\s\S]*?\n\s*(?:step\s+)?\d+[.)]\s+.+){2,}",
        re.IGNORECASE | re.MULTILINE,
    ),
    # "First, ... Second, ... Third, ..."
    re.compile(
        r"(?:first|step\s+1)[,:].*?(?:second|step\s+2|next)[,:]",
        re.IGNORECASE | re.DOTALL,
    ),
]

# Pattern to extract Jaco's step metadata
STEP_METADATA_PATTERN = re.compile(
    r"<!--\s*jaco-step:\s*({.*?})\s*-->", re.DOTALL
)


def extract_step_metadata(response: str) -> Optional[dict]:
    """Extract hidden step metadata from LLM response."""
    match = STEP_METADATA_PATTERN.search(response)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def strip_step_metadata(response: str) -> str:
    """Remove hidden step metadata from response before showing to user."""
    return STEP_METADATA_PATTERN.sub("", response).rstrip()


def detect_multi_step_leak(response: str) -> bool:
    """
    Detect if the LLM leaked a multi-step response when it should
    have given only one step.
    """
    for pattern in MULTI_STEP_PATTERNS:
        if pattern.search(response):
            return True
    return False


def split_first_step(response: str) -> tuple[str, str]:
    """
    Split a multi-step response into (first_step, remaining_steps).

    Returns the first step to show the user, and caches the rest.
    """
    lines = response.split("\n")
    first_step_lines = []
    remaining_lines = []
    found_second_step = False
    step_count = 0

    for line in lines:
        stripped = line.strip()
        # Detect numbered step starts
        if re.match(r"^\s*(?:step\s+)?\d+[.)]\s+", stripped, re.IGNORECASE):
            step_count += 1
            if step_count >= 2:
                found_second_step = True

        if found_second_step:
            remaining_lines.append(line)
        else:
            first_step_lines.append(line)

    first_step = "\n".join(first_step_lines).strip()
    remaining = "\n".join(remaining_lines).strip()

    return first_step, remaining


def is_advance_request(message: str) -> bool:
    """Check if user message is requesting the next step."""
    advance_phrases = [
        "next", "continue", "go on", "next step", "what's next",
        "done", "ok next", "okay next", "proceed", "and then",
        "what now", "now what",
    ]
    normalized = message.strip().lower().rstrip("?!.")
    return normalized in advance_phrases


def is_full_plan_request(message: str) -> bool:
    """Check if user is requesting the full plan."""
    full_plan_phrases = [
        "show all", "show all steps", "full plan", "all steps",
        "show me everything", "give me all", "the whole plan",
        "list all steps", "show everything",
    ]
    normalized = message.strip().lower().rstrip("?!.")
    return any(phrase in normalized for phrase in full_plan_phrases)


def inject_step_system_prompt(
    messages: list[dict], step_context: StepContext
) -> list[dict]:
    """
    Inject the step-by-step system prompt into the message list.

    If step mode is disabled for this chat, returns messages unchanged.
    """
    if not step_context.step_mode_enabled:
        return messages

    # Prepend or append to existing system message
    system_addition = STEP_MODE_SYSTEM_PROMPT

    if step_context.active_plan:
        system_addition += (
            f"\n\nCurrent context: You are on step {step_context.current_step} "
            f"of ~{step_context.total_steps_estimated} for: {step_context.plan_summary}. "
            f"Provide the next step only."
        )

    # Check if there's already a system message
    if messages and messages[0].get("role") == "system":
        messages[0]["content"] = messages[0]["content"] + "\n\n" + system_addition
    else:
        messages.insert(0, {"role": "system", "content": system_addition})

    return messages


def get_next_step(step_context: StepContext) -> Optional[dict]:
    """
    Advance to the next step in the plan.

    Returns a dict with 'content' (the next step text) and 'step_context'
    (updated context dict), or None if no plan is active or no steps remain.
    """
    if not step_context.active_plan:
        return None

    if not step_context.full_plan_cache:
        return None

    first_step, remaining = split_first_step(step_context.full_plan_cache)
    step_context.current_step += 1
    step_context.full_plan_cache = remaining if remaining else None

    if not step_context.full_plan_cache:
        step_context.active_plan = False

    return {
        "content": first_step,
        "step_context": step_context.to_dict(),
    }


def get_all_steps(step_context: StepContext) -> Optional[dict]:
    """
    Return the full plan with all remaining steps.

    Returns a dict with plan metadata, or None if no plan is active.
    """
    if not step_context.active_plan:
        return None

    return {
        "plan_summary": step_context.plan_summary,
        "full_plan": step_context.full_plan_cache or "",
        "current_step": step_context.current_step,
        "total_steps_estimated": step_context.total_steps_estimated,
    }
