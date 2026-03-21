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
from dotenv import load_dotenv
import random
import time
from pathlib import Path

load_dotenv(override=True)

_llm = AsyncOpenAI()   # reads OPENAI_API_KEY from env

# ── Helper ────────────────────────────────────────────────────────────────────

def _parse(result) -> dict | list:
    """Extract and JSON-parse the first content block of an MCP tool result."""
    if not result.content:
        raise ValueError("MCP tool returned empty content list")
    
    raw = result.content[0].text
    
    if not raw or not raw.strip():
        raise ValueError("MCP tool returned empty text response")
    
    # Strip markdown fences in various formats
    raw = raw.strip()
    if raw.startswith("```"):
        # Handle ```json ... ``` or ``` ... ```
        lines = raw.split("\n")
        # Remove first line (```json or ```) and last line (```)
        raw = "\n".join(lines[1:-1]).strip()
    
    # Sometimes the LLM prefixes with explanation text before the JSON
    # Try to find the first { or [ 
    if not raw.startswith("{") and not raw.startswith("["):
        brace = raw.find("{")
        bracket = raw.find("[")
        if brace == -1 and bracket == -1:
            raise ValueError(f"No JSON object found in response: {raw[:200]}")
        start = min(x for x in [brace, bracket] if x != -1)
        raw = raw[start:]
    
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

    # Write initial architecture to disk
    await ssd_session.call_tool("write_architecture", {
        "use_case":    state["problem_statement"][:40],
        "doc_type":    "initial",
        "content":     data["architecture_text"],
    })

    return {
        "architecture_id":      data["architecture_id"],
        "architecture_text":    data["architecture_text"],
        "current_future_index": 0,
        "critiques":            [],
        "tradeoffs":            [],
    }


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

    # Write final architecture to disk
    await ssd_session.call_tool("write_architecture", {
        "use_case": state["problem_statement"][:40],
        "doc_type":  "final",
        "content":   data["final_architecture"],
    })

    return {"final_architecture": data["final_architecture"]}


# Exact format spec extracted from the Excalidraw MCP read_me
EXCALIDRAW_SPEC = """
You are generating a static .excalidraw file. Follow these rules exactly.

== TEXT IN BOXES (CRITICAL) ==
NEVER use the "label" field. It does not work in static files.
For every rectangle, create a SEPARATE text element with containerId pointing to it:

  {"type":"rectangle","id":"r1","x":100,"y":85,"width":200,"height":70,"roundness":{"type":3},"backgroundColor":"#a5d8ff","fillStyle":"solid","strokeColor":"#4a9eed","strokeWidth":2}
  {"type":"text","id":"t1","x":150,"y":108,"width":100,"height":22,"text":"AWS SQS","fontSize":17,"strokeColor":"#1e1e1e","fontFamily":1,"textAlign":"center","verticalAlign":"middle","containerId":"r1"}

Text positioning rules:
  text.x      = rect.x + (rect.width - text.width) / 2
  text.y      = rect.y + (rect.height - text.height) / 2
  text.width  = len(text) * fontSize * 0.5
  text.height = fontSize * 1.25
  Always set containerId to the parent rectangle id.
  For multi-line text, increase rect height and set text.height = lines * fontSize * 1.25

== LAYOUT ==
- Row 1 (y=85):  main pipeline components left-to-right, 80px gaps
- Row 2 (y=230): API and security components
- Row 3 (y=380): observability/monitoring components
- Add a small label above each row: {"type":"text","id":"row1_lbl","x":60,"y":62,"width":200,"height":18,"text":"Event Pipeline","fontSize":13,"strokeColor":"#8b5cf6","fontFamily":1}
- Title: fontSize 24, centered above everything at y=15
- Minimum box size: 180x70
- Boxes with two-line text: height 80, text.height 45

== ARROWS ==
- Solid arrows for main data flow:  "strokeStyle":"solid","strokeWidth":2
- Dashed arrows for observability:  "strokeStyle":"dashed","strokeWidth":1,"strokeColor":"#f59e0b"
- Dashed arrows for API routing:    "strokeStyle":"dashed","strokeWidth":2,"strokeColor":"#22c55e"
- Arrow format: {"type":"arrow","id":"a1","x":280,"y":120,"width":80,"height":0,"points":[[0,0],[80,0]],"endArrowhead":"arrow","strokeColor":"#1e1e1e","strokeWidth":2}
- Vertical arrow (downward): points:[[0,0],[0,80]], width:0, height:80

== COLORS ==
- Event ingestion:   backgroundColor="#a5d8ff" strokeColor="#4a9eed"
- Processing:        backgroundColor="#d0bfff" strokeColor="#8b5cf6"
- Storage/cache:     backgroundColor="#c3fae8" strokeColor="#22c55e"
- API/output:        backgroundColor="#b2f2bb" strokeColor="#22c55e"
- Security/IAM:      backgroundColor="#ffd8a8" strokeColor="#f59e0b"
- Observability:     backgroundColor="#ffd8a8" strokeColor="#f59e0b"
- Cache/critical:    backgroundColor="#ffc9c9" strokeColor="#ef4444"

== COMPLETENESS ==
- Include EVERY component mentioned in the architecture text as a box
- Include EVERY data flow or connection as an arrow
- Observability components MUST have dashed arrows FROM pipeline components TO them
- Security components MUST be shown connected to what they protect
- Cache components sit beside storage with a bidirectional or labeled arrow

DO NOT include cameraUpdate or delete elements — static file only.
Output ONLY the JSON array, no markdown fences, no explanation.
"""

async def _architecture_to_excalidraw_elements(arch_text: str, label: str) -> str:
    response = await _llm.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": f"You are an expert at creating Excalidraw architecture diagrams.\n\n{EXCALIDRAW_SPEC}"
            },
            {
                "role": "user",
                "content": (
                    f"Create a complete Excalidraw diagram for this architecture.\n"
                    f"Title: '{label}'\n\n"
                    f"Architecture:\n{arch_text}\n\n"
                    "Before outputting JSON, think through:\n"
                    "1. List every component mentioned — each becomes a box\n"
                    "2. List every data flow — each becomes an arrow\n"
                    "3. Assign rows: pipeline=row1(y=85), API/security=row2(y=230), observability=row3(y=380)\n"
                    "4. Calculate x positions left-to-right with 80px gaps\n"
                    "5. For each box, calculate the paired text element coordinates\n\n"
                    "Output ONLY the JSON array."
                )
            }
        ],
        max_tokens=4000,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```json")[-1].strip("` \n")
    return raw


def _validate_elements(elements: list) -> list:
    """Warn about common issues that produce blank or broken diagrams."""
    ids = {el["id"] for el in elements if "id" in el}
    for el in elements:
        if el.get("type") == "text":
            cid = el.get("containerId")
            if cid and cid not in ids:
                print(f"  [warn] text '{el.get('text','')}' has containerId={cid} which doesn't exist")
            if not cid and el.get("fontSize", 20) < 20:
                print(f"  [warn] text '{el.get('text','')}' has no containerId — may float outside box")
        if el.get("type") == "arrow":
            if el.get("width", 0) == 0 and el.get("height", 0) == 0:
                print(f"  [warn] arrow '{el.get('id')}' has zero size — will be invisible")
    return elements


async def draw_diagram_node(
    state: DesignState,
    ex_session: ClientSession,
    phase: str,
) -> dict:
    if phase == "initial":
        arch_text = state["architecture_text"]
        label     = "Initial Architecture"
        url_key   = "initial_diagram_url"
        filename  = "diagram_initial.excalidraw"
    else:
        arch_text = state["final_architecture"]
        label     = "Final Governed Architecture"
        url_key   = "final_diagram_url"
        filename  = "diagram_final.excalidraw"

    print(f"\n[draw_{phase}] Generating diagram for: {label}")

    elements_raw = await _architecture_to_excalidraw_elements(arch_text, label)

    try:
        elements = json.loads(elements_raw)
        if isinstance(elements, dict):
            elements = elements.get("elements", [])
    except json.JSONDecodeError as e:
        print(f"[draw_{phase}] Invalid JSON: {e}")
        return {url_key: None}

    # Strip pseudo-elements not valid in static files
    static_types = {"rectangle", "ellipse", "diamond", "arrow", "text", "line"}
    elements = [el for el in elements if el.get("type") in static_types]

    # Validate and warn about common issues
    elements = _validate_elements(elements)
    print(f"[draw_{phase}] {len(elements)} elements after filtering")

    excalidraw_file = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {"viewBackgroundColor": "#ffffff"},
        "files": {}
    }

    safe = lambda s: "".join(c if c.isalnum() or c in " -_" else "_" for c in s).strip()
    use_case = safe(state["problem_statement"][:40])
    output_dir = Path(__file__).parent.parent / "architectures" / use_case
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(excalidraw_file, f, indent=2)

    print(f"[draw_{phase}] Saved: {output_path}")
    print(f"[draw_{phase}] Open https://excalidraw.com → File → Open to view")

    return {url_key: str(output_path)}
