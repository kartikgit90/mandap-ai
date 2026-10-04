"""One place where the backend talks to Claude.

Every agent calls `ask()` here instead of calling Claude directly. That gives us:
- one switch for the provider (Anthropic directly now, Google Vertex AI later)
- cost and token tracking on every single call
- one place to add caching, retries and cost caps later
"""

from dataclasses import dataclass
from functools import lru_cache
import time
from typing import Literal

import anthropic

from app.config import get_settings

Tier = Literal["fast", "smart"]  # fast = Haiku (most work), smart = Sonnet (planner)

# Price per million tokens in USD (input, output). Source: Claude pricing page, Oct 2026.
PRICES_USD = {
    "fast": (1.00, 5.00),   # Claude Haiku 4.5
    "smart": (2.00, 10.00),  # Claude Sonnet 5.5
}


@dataclass
class LLMResult:
    text: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_inr: float
    latency_ms: int


def model_id(tier: Tier) -> str:
    s = get_settings()
    if s.llm_provider == "vertex":
        return s.vertex_model_fast if tier == "fast" else s.vertex_model_smart
    return s.anthropic_model_fast if tier == "fast" else s.anthropic_model_smart


@lru_cache
def _client():
    s = get_settings()
    if s.llm_provider == "vertex":
        # Uses the service's own Google identity on Cloud Run: no key needed.
        return anthropic.AnthropicVertex(region="global", project_id=s.gcp_project_id)
    if not s.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=s.anthropic_api_key)


def cost_inr(tier: Tier, tokens_in: int, tokens_out: int) -> float:
    price_in, price_out = PRICES_USD[tier]
    usd = tokens_in / 1e6 * price_in + tokens_out / 1e6 * price_out
    return round(usd * get_settings().usd_to_inr, 4)


def ask(prompt: str, *, system: str = "", tier: Tier = "fast", max_tokens: int = 512) -> LLMResult:
    """Send one message to Claude and return the reply with its cost."""
    started = time.perf_counter()
    msg = _client().messages.create(
        model=model_id(tier),
        max_tokens=max_tokens,
        system=system or anthropic.NOT_GIVEN,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    return LLMResult(
        text=text,
        model=msg.model,
        tokens_in=msg.usage.input_tokens,
        tokens_out=msg.usage.output_tokens,
        cost_inr=cost_inr(tier, msg.usage.input_tokens, msg.usage.output_tokens),
        latency_ms=int((time.perf_counter() - started) * 1000),
    )
