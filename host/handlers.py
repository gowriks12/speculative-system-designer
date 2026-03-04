"""
Sampling and elicitation callbacks for the MCP ClientSession.

Sampling:    the SSD server calls back into the host to run an LLM completion.
Elicitation: the SSD server asks the host to collect a decision.

ELICITATION_MODE (set in .env):
    "llm"   — an LLM auto-selects the tradeoff option (fully agentic, default)
    "human" — LangGraph interrupt() pauses the graph; resume with:
              graph.ainvoke(Command(resume="B"), config=config)
"""

import json
import os
from mcp import ClientSession, types
from mcp.shared.context import RequestContext
from mcp.types import (
    ElicitRequestParams,
    ElicitResult,
    CreateMessageRequestParams,
    CreateMessageResult,
)
from openai import AsyncOpenAI

ELICITATION_MODE = os.getenv("ELICITATION_MODE", "llm")
LLM_MODEL        = os.getenv("LLM_MODEL", "gpt-4o-mini")

_client = AsyncOpenAI()   # reads OPENAI_API_KEY from env


# ── Sampling ──────────────────────────────────────────────────────────────────

async def sampling_handler(
    context: RequestContext[ClientSession, None],
    params: CreateMessageRequestParams,
) -> CreateMessageResult:
    """Forwards the server's sampling request to the OpenAI LLM."""
    messages = [
        {"role": m.role, "content": m.content.text}
        for m in params.messages
    ]
    response = await _client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        max_tokens=params.max_tokens or 800,
    )
    return CreateMessageResult(
        role="assistant",
        content=types.TextContent(
            type="text",
            text=response.choices[0].message.content,
        ),
        model=LLM_MODEL,
        stopReason="endTurn",
    )


# ── Elicitation ───────────────────────────────────────────────────────────────

async def elicitation_handler(
    context: RequestContext[ClientSession, None],
    params: ElicitRequestParams,
) -> ElicitResult:
    """
    In "llm" mode:   an LLM reads the options and picks the most pragmatic one.
    In "human" mode: interrupt() pauses the graph for an external decision.
    """
    if ELICITATION_MODE == "human":
        from langgraph.types import interrupt
        selection = interrupt({"message": params.message})
        return ElicitResult(action="accept", content={"selected_option": selection})

    # LLM auto-select
    response = await _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a pragmatic system architect making tradeoff decisions. "
                    "You will be shown several options labelled A, B, C. "
                    "Pick the option that best balances long-term maintainability "
                    "with near-term delivery speed. "
                    "Respond ONLY with valid JSON: {\"selected_option\": \"<A|B|C>\"}"
                ),
            },
            {"role": "user", "content": params.message},
        ],
        max_tokens=50,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```json")[-1].strip("` \n")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"selected_option": "A"}

    return ElicitResult(action="accept", content=parsed)
