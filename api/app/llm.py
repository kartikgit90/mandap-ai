"""One place where the backend talks to Claude.

Every agent calls `ask()` here instead of calling Claude directly. That gives us:
- one switch for the provider (Anthropic directly now, Google Vertex AI later)
- cost and token tracking on every single call
- one place to add caching, retries and cost caps later
"""

from dataclasses import dataclass
from functools import lru_cache
import json
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


@dataclass
class AgentResult:
    text: str
    tool_calls: list  # [(name, input, result)]
    tokens_in: int
    tokens_out: int
    cost_inr: float
    model: str
    stopped_early: str | None = None


def run_agent(
    *,
    system: str,
    messages: list[dict],
    tools: list[dict],
    handlers: dict,
    tier: Tier = "fast",
    max_steps: int = 6,
    cost_cap_inr: float = 10.0,
    max_tokens: int = 1200,
) -> AgentResult:
    """Run Claude with tools until it gives a final answer.

    Safety limits: at most `max_steps` rounds of tool calls, and a hard cost cap per request.
    Tools are plain Python functions in `handlers`; Claude can only call what is listed.
    """
    msgs = list(messages)
    calls, t_in, t_out, cost, model = [], 0, 0, 0.0, model_id(tier)
    # The system prompt and tool list are the same every turn, so cache them (cheaper, faster).
    system_blocks = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

    for step in range(max_steps + 1):
        resp = _client().messages.create(
            model=model, max_tokens=max_tokens, system=system_blocks, tools=tools, messages=msgs
        )
        t_in += resp.usage.input_tokens
        t_out += resp.usage.output_tokens
        cost = cost_inr(tier, t_in, t_out)
        model = resp.model

        tool_uses = [b for b in resp.content if getattr(b, "type", "") == "tool_use"]
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        if resp.stop_reason != "tool_use" or not tool_uses:
            return AgentResult(text, calls, t_in, t_out, cost, model)
        if step == max_steps:
            return AgentResult(text or "I need more steps than allowed for this. Could you narrow the request?",
                               calls, t_in, t_out, cost, model, stopped_early="max_steps")
        if cost > cost_cap_inr:
            return AgentResult(text or "This request got too long. Could you narrow it down?",
                               calls, t_in, t_out, cost, model, stopped_early="cost_cap")

        msgs.append({"role": "assistant", "content": [b.model_dump() for b in resp.content]})
        results = []
        for tu in tool_uses:
            fn = handlers.get(tu.name)
            try:
                out = fn(**(tu.input or {})) if fn else {"error": f"unknown tool {tu.name}"}
            except Exception as e:  # report tool errors back to Claude so it can recover
                out = {"error": str(e)}
            calls.append((tu.name, tu.input, out))
            results.append({"type": "tool_result", "tool_use_id": tu.id, "content": json.dumps(out, default=str)})
        msgs.append({"role": "user", "content": results})

    return AgentResult("", calls, t_in, t_out, cost, model, stopped_early="max_steps")


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
