"""
LangGraph nodes.
Each node wraps one MCP tool call.  The sessions are injected via closure
in graph.py so every node keeps the clean (state) -> dict signature that
LangGraph requires.
"""

import json
from mcp import ClientSession
from openai import AsyncOpenAI
from state import DesignState

_llm = AsyncOpenAI()   # reads OPENAI_API_KEY from env


# ── Helper ────────────────────────────────────────────────────────────────────

def _parse(result) -> dict | list:
    """Extract and JSON-parse the first content block of an MCP tool result."""
    raw = result.content[0].text
    if raw.startswith("```"):
        raw = raw.split("```json")[-1].strip("` \n")
    return json.loads(raw)


# ── Startup helper ────────────────────────────────────────────────────────────

async def fetch_future_ids(session: ClientSession) -> list[str]:
    """
    Calls list_futures_tool on the SSD server so the host never needs to
    hardcode future names.
    """
    result = await session.call_tool("list_futures_tool", {})
    data = _parse(result)
    return list(data.keys())


# ── Nodes ─────────────────────────────────────────────────────────────────────

async def generate_architecture_node(
    state: DesignState,
    ssd_session: ClientSession,
) -> dict:
    """Calls generate_architecture_tool and seeds the state for the loop."""
    result = await ssd_session.call_tool(
        "generate_architecture_tool",
        {"problem_statement": state["problem_statement"]},
    )
    data = _parse(result)

    print(f"\n[generate] Architecture ID : {data['architecture_id']}")
    print(f"[generate] Architecture:\n{data['architecture_text']}\n")

    return {
        "architecture_id":      data["architecture_id"],
        "architecture_text":    data["architecture_text"],
        "current_future_index": 0,
        "critiques":            [],
        "tradeoffs":            [],
    }


async def draw_diagram_node(
    state: DesignState,
    ex_session: ClientSession,
    phase: str,   # "initial" | "final"
) -> dict:
    """
    1. Asks an LLM to convert the architecture text into Excalidraw elements JSON.
    2. Sends that JSON to the Excalidraw MCP server via create_drawing.
    3. Stores the returned diagram URL in state.
    """
    if phase == "initial":
        arch_text = state["architecture_text"]
        label     = "Initial Architecture"
        url_key   = "initial_diagram_url"
    else:
        arch_text = state["final_architecture"]
        label     = "Final Governed Architecture"
        url_key   = "final_diagram_url"

    print(f"\n[draw_{phase}] Generating Excalidraw elements for: {label}")

    elements_json = await _architecture_to_excalidraw_elements(arch_text, label)

    result = await ex_session.call_tool(
        "create_drawing",
        {"elements": elements_json},
    )

    diagram_url = result.content[0].text
    print(f"[draw_{phase}] Diagram URL: {diagram_url}")

    return {url_key: diagram_url}


async def _architecture_to_excalidraw_elements(arch_text: str, label: str) -> str:
    """
    Uses the LLM to translate architecture prose into a valid Excalidraw
    elements JSON array (no markdown fences, no explanation).
    """
    response = await _llm.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert at converting system architecture descriptions "
                    "into Excalidraw diagrams. Output ONLY a valid JSON array of "
                    "Excalidraw elements — no explanation, no markdown fences.\n"
                    "Rules:\n"
                    "- Rectangles (type: rectangle) for services/components\n"
                    "- Arrows (type: arrow) for data flows with endArrowhead: 'arrow'\n"
                    "- A text element for the diagram title\n"
                    "- Reasonable x/y coordinates so the layout is readable\n"
                    "- Each element must have: type, id, x, y, width, height"
                ),
            },
            {
                "role": "user",
                "content": f"Title: {label}\n\nArchitecture:\n{arch_text}",
            },
        ],
        max_tokens=2000,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```json")[-1].strip("` \n")
    return raw


async def simulate_future_node(
    state: DesignState,
    ssd_session: ClientSession,
    future_ids: list[str],
) -> dict:
    """Simulates the next future in the list and appends the critique to state."""
    idx       = state["current_future_index"]
    future_id = future_ids[idx]

    print(f"\n[simulate] Future [{idx + 1}/{len(future_ids)}]: {future_id}")

    result = await ssd_session.call_tool(
        "simulate_future_tool",
        {
            "architecture_id": state["architecture_id"],
            "future_id":       future_id,
        },
    )
    data    = _parse(result)
    critique = data["critique"]

    print(f"[simulate] Summary: {critique['summary']}")

    return {
        "critiques":            state["critiques"] + [critique],
        "current_future_index": idx + 1,
    }


async def propose_tradeoff_node(
    state: DesignState,
    ssd_session: ClientSession,
) -> dict:
    """
    Proposes tradeoff options for the most-recent critique.
    The server triggers elicitation, which is handled by elicitation_handler.
    """
    latest = state["critiques"][-1]

    print(f"\n[tradeoff] Resolving critique for future: {latest['future']}")

    result = await ssd_session.call_tool(
        "propose_tradeoff_tool",
        {
            "architecture_id":  state["architecture_id"],
            "critique_id":      latest["id"],
            "critique_summary": latest["summary"],
        },
    )
    data = _parse(result)

    print(
        f"[tradeoff] Selected: {data.get('selected', {}).get('id', '?')} — "
        f"{data.get('selected', {}).get('statement', '')}"
    )

    return {"tradeoffs": state["tradeoffs"] + [data]}


async def finalize_architecture_node(
    state: DesignState,
    ssd_session: ClientSession,
) -> dict:
    """Calls finalize_architecture_tool to produce the governed architecture."""
    print("\n[finalize] Generating final architecture...")

    result = await ssd_session.call_tool(
        "finalize_architecture_tool",
        {"architecture_id": state["architecture_id"]},
    )
    data = _parse(result)

    print("\n=== FINAL ARCHITECTURE ===")
    print(data["final_architecture"])

    return {"final_architecture": data["final_architecture"]}
