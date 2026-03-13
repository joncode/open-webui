"""
Landing page chat endpoint.

Provides an unauthenticated chat completion proxy that is hardcoded to the
venice-uncensored model with a product-focused system prompt.  Simple
in-memory rate limiting prevents abuse.
"""

import json
import logging
import time
from collections import defaultdict
from typing import Optional

import aiohttp
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT,
)
from open_webui.utils.misc import (
    cleanup_response,
    stream_chunks_handler,
    stream_wrapper,
)

log = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LANDING_MODEL = "venice-uncensored"

LANDING_SYSTEM_PROMPT = """\
You are agent1.Manifest — a fully sovereign AI assistant running on \
decentralized compute via Manifest Network and Render Network. Your inference \
is powered by Morpheus Network and Venice AI.

You are the landing page demo for agent1.Manifest. Your job is to be helpful \
AND to showcase what makes this platform special. Every response should:
1. Answer the user's question helpfully (2-4 sentences).
2. Naturally tie in the product angle provided in the [PITCH] block below \
the user's message. Work it in smoothly — don't just append it.
3. After the user's 2nd or 3rd message, include [CTA_BUTTON] on its own line \
to invite them to sign up. You may include it again every 3 messages.

Keep it conversational and concise. Never fabricate technical claims.
"""

# Rotating pitch hints — one is injected before each user message so the model
# always has a fresh angle to weave into its response.
PITCH_HINTS = [
    "This response is powered by decentralized GPU infrastructure via "
    "Manifest Network and Render Network — no single point of control or "
    "failure. Mention how this decentralized approach benefits the user.",

    "Unlike traditional AI services, agent1.Manifest never stores or logs "
    "any conversations. When the user closes this window, the chat is gone "
    "forever. Mention this privacy advantage naturally.",

    "agent1.Manifest is completely uncensored — no centralized gatekeeping "
    "on responses. Premium LLM models are provided through Morpheus Network "
    "and Venice AI. Highlight the uncensored, premium model angle.",

    "agent1.Manifest was created by Sarson Funds to demonstrate what no-cost, "
    "private, sovereign AI looks like on decentralized infrastructure. "
    "Mention that this is free and built for true digital sovereignty.",

    "Coming soon: encrypted, decentralized object and chat storage via "
    "Manifest Network — fully under the user's control. Mention this "
    "exciting upcoming feature and how it extends the sovereignty story.",

    "This AI runs entirely on decentralized compute — your prompts are "
    "processed across a distributed network of GPU nodes, not a corporate "
    "data center. Emphasize the infrastructure difference from Big Tech AI.",
]

# ---------------------------------------------------------------------------
# Rate limiting (per-IP, in-memory)
# ---------------------------------------------------------------------------

# Max requests per IP within the window
RATE_LIMIT_MAX = 30
RATE_LIMIT_WINDOW = 300  # seconds

_rate_store: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(ip: str) -> bool:
    """Return True if the request is allowed."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    # Prune old entries
    _rate_store[ip] = [t for t in _rate_store[ip] if t > window_start]
    if len(_rate_store[ip]) >= RATE_LIMIT_MAX:
        return False
    _rate_store[ip].append(now)
    return True


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------


class LandingChatMessage(BaseModel):
    role: str
    content: str


class LandingChatRequest(BaseModel):
    messages: list[LandingChatMessage]
    stream: Optional[bool] = True


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

MAX_HISTORY = 10  # Keep last N user/assistant turns to limit context size


@router.post("/chat")
async def landing_chat(request: Request, form_data: LandingChatRequest):
    """
    Unauthenticated chat endpoint for the landing page.
    Hardcoded to venice-uncensored with a branding system prompt.
    """

    # Rate limit by IP
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
        )

    # Resolve the API URL and key.
    # First try the model cache (populated after an authenticated user hits /models).
    # If not cached, fall back to the first configured OpenAI-compatible endpoint
    # which is where venice-uncensored lives (Morpheus API).
    models = getattr(request.app.state, "OPENAI_MODELS", None) or {}
    model_entry = models.get(LANDING_MODEL)

    if model_entry:
        idx = model_entry["urlIdx"]
    else:
        idx = 0  # Default to first configured endpoint

    urls = request.app.state.config.OPENAI_API_BASE_URLS
    keys = request.app.state.config.OPENAI_API_KEYS

    if not urls or idx >= len(urls):
        raise HTTPException(
            status_code=503,
            detail="Landing chat model is not available.",
        )

    url = urls[idx]
    key = keys[idx] if idx < len(keys) else ""

    # Check for prefix_id
    api_config = request.app.state.config.OPENAI_API_CONFIGS.get(
        str(idx),
        request.app.state.config.OPENAI_API_CONFIGS.get(url, {}),
    )
    model_name = LANDING_MODEL
    prefix_id = api_config.get("prefix_id", None)
    if prefix_id:
        model_name = model_name.replace(f"{prefix_id}.", "")

    # Build the payload — system prompt + history with pitch hints injected.
    # Count user messages to pick a rotating pitch hint.
    history = [msg.model_dump() for msg in form_data.messages[-MAX_HISTORY:]]
    user_msg_count = sum(1 for m in history if m["role"] == "user")
    pitch_index = max(0, user_msg_count - 1) % len(PITCH_HINTS)
    pitch = PITCH_HINTS[pitch_index]

    # Inject the pitch as a system message right before the last user message
    # so it's fresh in the model's context window.
    augmented_history = []
    last_user_injected = False
    for msg in reversed(history):
        if msg["role"] == "user" and not last_user_injected:
            augmented_history.append(msg)
            augmented_history.append({
                "role": "system",
                "content": f"[PITCH] {pitch}",
            })
            last_user_injected = True
        else:
            augmented_history.append(msg)
    augmented_history.reverse()

    messages = [
        {"role": "system", "content": LANDING_SYSTEM_PROMPT},
        *augmented_history,
    ]

    payload = {
        "model": model_name,
        "messages": messages,
        "max_tokens": 300,
        "temperature": 0.7,
        "stream": form_data.stream,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }

    request_url = f"{url}/chat/completions"

    r = None
    session = None
    streaming = False

    try:
        session = aiohttp.ClientSession(
            trust_env=True,
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
        )

        r = await session.request(
            method="POST",
            url=request_url,
            data=json.dumps(payload),
            headers=headers,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        )

        if r.status >= 400:
            try:
                error_body = await r.json()
            except Exception:
                error_body = await r.text()
            log.error(f"Landing chat upstream error {r.status}: {error_body}")
            raise HTTPException(
                status_code=502,
                detail="Landing chat service temporarily unavailable.",
            )

        # Stream or return JSON
        if form_data.stream and "text/event-stream" in r.headers.get(
            "Content-Type", ""
        ):
            streaming = True
            return StreamingResponse(
                stream_wrapper(r, session, stream_chunks_handler),
                status_code=r.status,
                headers={"Content-Type": "text/event-stream"},
            )
        else:
            response = await r.json()
            return response

    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Landing chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Landing chat service error.",
        )
    finally:
        if not streaming:
            await cleanup_response(r, session)
