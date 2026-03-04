"""
Speculative System Designer — MCP Server
========================================
Generates, stress-tests, and governs software architectures through:
  - Root constraints  (non-negotiable principles loaded from data/roots.json)
  - Futures           (pessimistic scenarios loaded from data/futures.json)
  - Critiques         (structured LLM feedback per future)
  - Tradeoffs         (human-accepted compromises that shape the final output)

Transport: stdio (default for Claude Desktop) or streamable-http.
Change the last line of this file to switch transports.
"""

import json
from pathlib import Path
from uuid import uuid4
from datetime import datetime

from mcp.server.fastmcp import FastMCP, Context
from mcp.types import SamplingMessage, TextContent
from pydantic import BaseModel, Field

from architectures import submit_architecture
from critiques import Critique, save_critique, CRITIQUE_STORE
from futures import load_futures
from roots import load_roots, format_roots_for_prompt
from store import REVIEW_STORE
from declare_tradeoff import declare_tradeoff

# ---------------------------------------------------------------------------
# Server initialisation
# ---------------------------------------------------------------------------

mcp = FastMCP("SpeculativeSystemDesigner")

# Load static data once at startup so tools never hit disk on every call.
FUTURES: dict = load_futures()
ROOTS: dict = load_roots()
OUTPUT_DIR = Path(__file__) / "architectures"  # pre-defined output location
OUTPUT_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Pydantic schema used by MCP Elicitation in propose_tradeoff_tool
# ---------------------------------------------------------------------------

class TradeoffSelection(BaseModel):
    """Schema sent to the MCP client when asking the user to pick a tradeoff."""

    selected_option: str = Field(
        description="Enter the ID of the tradeoff option you accept (A, B, or C)."
    )


# ---------------------------------------------------------------------------
# Resources — readable by any MCP client
# ---------------------------------------------------------------------------

@mcp.resource("roots://governance")
def roots_resource() -> dict:
    """Expose the root constraints so clients can inspect governance rules."""
    return ROOTS


@mcp.resource("roots://futures")
def futures_resource() -> dict:
    """Expose the futures catalogue so clients know which scenarios exist."""
    return FUTURES


# ---------------------------------------------------------------------------
# Tool 1 — generate_architecture_tool
# ---------------------------------------------------------------------------

@mcp.tool()
async def generate_architecture_tool(ctx: Context, problem_statement: str) -> dict:
    """
    Generate a system architecture that satisfies all root constraints.

    The tool uses MCP Sampling to delegate the LLM call back to the client,
    meaning the client's chosen model (e.g. Claude Sonnet) performs the actual
    generation. The server injects the root constraints into the prompt so the
    client cannot bypass them.

    The generated architecture is immediately saved to REVIEW_STORE so that
    subsequent tools (simulate, evaluate, finalize) can reference it by ID.

    Args:
        problem_statement: Plain-language description of the system to design.
            Example: "A backend that ingests IoT sensor events and exposes
            analytics dashboards to 10,000 customers."

    Returns:
        {
            "status": "architecture_generated",
            "architecture_id": "<uuid>",
            "architecture_text": "<full architecture description>"
        }
    """
    roots = load_roots()
    formatted_roots = format_roots_for_prompt(roots)

    result = await ctx.session.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=(
                        "You are a senior system architect.\n\n"
                        "Design an architecture for the following problem.\n\n"
                        f"Problem:\n{problem_statement}\n\n"
                        "You MUST comply with the following constitutional root constraints:\n\n"
                        f"{formatted_roots}\n\n"
                        "For each root constraint, briefly explain how your design satisfies it.\n\n"
                        "Then provide the final architecture description in 5 to 8 sentences."
                    ),
                ),
            )
        ],
        max_tokens=800,
    )

    architecture_text = result.content.text
    saved = submit_architecture(architecture_text)

    return {
        "status": "architecture_generated",
        "architecture_id": saved["architecture_id"],
        "architecture_text": architecture_text,
    }


# ---------------------------------------------------------------------------
# Tool 2 — simulate_future_tool
# ---------------------------------------------------------------------------

@mcp.tool()
async def simulate_future_tool(
    ctx: Context,
    architecture_id: str,
    future_id: str,
) -> dict:
    """
    Stress-test a saved architecture against a single future scenario.

    Each future (defined in data/futures.json) has a `review_prompt` that
    instructs the LLM to act as a pessimistic review board. The LLM's response
    is expected as JSON with `summary` (str) and `risks` (list[str]).

    A Critique object is created and stored; its ID is also appended to the
    architecture's review record in REVIEW_STORE.

    Args:
        architecture_id: UUID returned by generate_architecture_tool or
            submit_architecture_tool.
        future_id: Key from data/futures.json (e.g. "scaling",
            "security_abuse", "regulatory_compliance").

    Returns:
        {
            "status": "critique_generated",
            "critique": {
                "id": "<uuid>",
                "future": "<future_id>",
                "summary": "...",
                "risks": ["...", "..."],
                "required_tradeoff": "Unresolved",
                "resolved": false
            }
        }

    Raises:
        Returns {"status": "error", "reason": "..."} if architecture_id or
        future_id is unknown.
    """
    review = REVIEW_STORE.get(architecture_id)
    if not review:
        return {"status": "error", "reason": f"Unknown architecture_id: {architecture_id}"}

    if future_id not in FUTURES:
        return {"status": "error", "reason": f"Unknown future_id: {future_id}"}

    architecture_text = review["initial_architecture"]
    future = FUTURES[future_id]
    review_prompt = future["review_prompt"]

    result = await ctx.session.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(type="text", text=review_prompt),
            ),
            SamplingMessage(
                role="user",
                content=TextContent(type="text", text=architecture_text),
            ),
        ],
        max_tokens=400,
    )

    raw_text = result.content.text.strip()

    # Strip markdown fences if the model wrapped the JSON
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```json")[-1].strip().strip("```").strip()

    parsed = json.loads(raw_text)

    critique = Critique(
        id=str(uuid4()),
        future=future_id,
        summary=parsed["summary"],
        risks=parsed["risks"],
        required_tradeoff="Unresolved",
    )
    save_critique(critique)
    review["critiques"].append(critique.id)

    return {
        "status": "critique_generated",
        "critique": critique.model_dump(),
    }


# ---------------------------------------------------------------------------
# Tool 3 — propose_tradeoff_tool
# ---------------------------------------------------------------------------

@mcp.tool()
async def propose_tradeoff_tool(
    ctx: Context,
    architecture_id: str,
    critique_id: str,
    critique_summary: str,
) -> dict:
    """
    Present three tradeoff options for a critique and ask the user to choose one.

    This tool has two phases:
      1. **LLM Sampling** — the server asks the client LLM to generate exactly
         three tradeoff options (each with an id, statement, sacrifice, and
         benefit) as JSON.
      2. **MCP Elicitation** — the server presents those options to the human
         via the client's UI and waits for a selection.

    Once the user accepts an option, the tradeoff is recorded via
    declare_tradeoff and the critique is marked resolved.

    Args:
        architecture_id: UUID of the architecture being reviewed.
        critique_id: UUID of the Critique this tradeoff resolves.
        critique_summary: Human-readable description of the problem (from the
            critique). Used as context for option generation.

    Returns:
        On success:
            {"status": "tradeoff_declared", "selected": {option object}}
        On cancellation:
            {"status": "cancelled"}
        On invalid selection:
            {"status": "error", "message": "..."}
    """
    # Phase 1: Generate structured tradeoff options via LLM Sampling
    result = await ctx.session.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=(
                        "You are an experienced system architect.\n"
                        "Given the critique below, propose EXACTLY THREE distinct tradeoff options.\n"
                        "Respond ONLY in JSON format:\n\n"
                        "{\n"
                        '  "options": [\n'
                        '    {"id": "A", "statement": "...", "sacrifice": "...", "benefit": "..."},\n'
                        '    {"id": "B", "statement": "...", "sacrifice": "...", "benefit": "..."},\n'
                        '    {"id": "C", "statement": "...", "sacrifice": "...", "benefit": "..."}\n'
                        "  ]\n"
                        "}\n\n"
                        f"Critique:\n{critique_summary}"
                    ),
                ),
            )
        ],
        max_tokens=400,
    )

    raw_text = result.content.text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```json")[-1].strip().strip("```").strip()

    parsed = json.loads(raw_text)
    options: list[dict] = parsed["options"]

    options_text = "\n\n".join(
        f"{o['id']}:\n"
        f"  Statement : {o['statement']}\n"
        f"  Sacrifice : {o['sacrifice']}\n"
        f"  Benefit   : {o['benefit']}"
        for o in options
    )

    # Phase 2: Ask the human to choose via MCP Elicitation
    elicitation = await ctx.elicit(
        message=f"Select the tradeoff you are willing to accept:\n\n{options_text}",
        schema=TradeoffSelection,
    )

    if elicitation.action != "accept" or not elicitation.data:
        return {"status": "cancelled"}

    selected_id = elicitation.data.selected_option.strip().upper()
    valid_ids = {o["id"] for o in options}

    if selected_id not in valid_ids:
        return {
            "status": "error",
            "message": f"Invalid selection '{selected_id}'. Must be one of {sorted(valid_ids)}.",
        }

    selected_option = next(o for o in options if o["id"] == selected_id)
    declare_tradeoff(architecture_id, critique_id, selected_option["statement"])

    return {
        "status": "tradeoff_declared",
        "selected": selected_option,
    }


# ---------------------------------------------------------------------------
# Tool 4 — evaluate_architecture_tool  (orchestrator)
# ---------------------------------------------------------------------------

@mcp.tool()
async def evaluate_architecture_tool(ctx: Context, architecture_id: str) -> dict:
    """
    Run the full evaluation pipeline for a saved architecture.

    This is the primary high-level tool. It orchestrates:
      1. simulate_future_tool for every future in data/futures.json
      2. propose_tradeoff_tool for every resulting critique
      3. finalize_architecture_tool once all tradeoffs are declared

    The user will be prompted (via MCP Elicitation) once per future to select
    a tradeoff. After all choices are made, a final governed architecture is
    produced and returned.

    Args:
        architecture_id: UUID returned by generate_architecture_tool.

    Returns:
        {
            "status": "evaluation_complete",
            "final_architecture": { ...finalize_architecture_tool response... }
        }
    """
    critiques = []
    for future_id in FUTURES:
        result = await simulate_future_tool(ctx, architecture_id=architecture_id, future_id=future_id)
        critiques.append(result["critique"])

    for critique in critiques:
        await propose_tradeoff_tool(
            ctx,
            architecture_id=architecture_id,
            critique_id=critique["id"],
            critique_summary=critique["summary"],
        )

    final_architecture = await finalize_architecture_tool(ctx, architecture_id=architecture_id)

    return {
        "status": "evaluation_complete",
        "final_architecture": final_architecture,
    }


# ---------------------------------------------------------------------------
# Tool 5 — finalize_architecture_tool
# ---------------------------------------------------------------------------

@mcp.tool()
async def finalize_architecture_tool(ctx: Context, architecture_id: str) -> dict:
    """
    Produce the final architecture incorporating all accepted tradeoffs.

    Refused if no tradeoffs have been declared — the server enforces that
    every critique must be resolved before a final architecture is issued.

    Uses MCP Sampling to delegate synthesis to the client LLM, passing both
    the original architecture text and the list of declared tradeoff statements.

    Args:
        architecture_id: UUID of the architecture to finalize.

    Returns:
        On success:
            {"status": "finalized", "final_architecture": "<text>"}
        On missing data:
            {"status": "error", "reason": "..."}
    """
    review = REVIEW_STORE.get(architecture_id)
    if not review:
        return {"status": "error", "reason": f"Unknown architecture_id: {architecture_id}"}

    tradeoffs = review["tradeoffs"]
    if not tradeoffs:
        return {
            "status": "error",
            "reason": "No tradeoffs declared. Run evaluate_architecture_tool first.",
        }

    initial_arch = review["initial_architecture"]
    tradeoff_text = "\n".join(f"- {t['statement']}" for t in tradeoffs)

    result = await ctx.session.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=(
                        "You previously proposed this architecture:\n\n"
                        f"{initial_arch}\n\n"
                        "The following tradeoffs have been explicitly accepted by the team:\n\n"
                        f"{tradeoff_text}\n\n"
                        "Produce a final architecture that clearly and concretely reflects these tradeoffs. "
                        "Be technical and specific. Keep the complete architecture concise within 10 sentences."
                    ),
                ),
            )
        ],
        max_tokens=600,
    )

    final_arch = result.content.text
    review["final_architecture"] = final_arch

    return {
        "status": "finalized",
        "final_architecture": final_arch,
    }


# ---------------------------------------------------------------------------
# Tool 6 — List root constraints tool  
# ---------------------------------------------------------------------------

@mcp.tool()
def list_roots_scope():
    """List the future scopes available to simulate"""
    return list(ROOTS.keys())

# ---------------------------------------------------------------------------
# Tool 7 — List futures tool  
# ---------------------------------------------------------------------------

@mcp.tool()
def list_futures_scope():
    """List the future scopes available to simulate"""
    return list(FUTURES.keys())

# ---------------------------------------------------------------------------
# Tool 8 — Write architecture information to disk tool
# ---------------------------------------------------------------------------

@mcp.tool()
def write_architecture(use_case: str, doc_type: str, content: str, future_name: str = "") -> str:
    """Write an architecture document to the architectures/<use_case>/ folder.

    doc_type must be one of: 'initial', 'simulated_future', 'final'.
    For 'simulated_future', also provide future_name.
    """
    safe = lambda s: "".join(c if c.isalnum() or c in " -_" else "_" for c in s).strip()

    folder = OUTPUT_DIR / safe(use_case)
    folder.mkdir(parents=True, exist_ok=True)

    match doc_type:
        case "initial":
            filename = "Initial Architecture.txt"
        case "simulated_future":
            filename = f"Simulated Future - {safe(future_name)}.txt"
        case "final":
            filename = "Final Architecture.txt"
        case _:
            return f"Unknown doc_type '{doc_type}'. Use: initial, simulated_future, or final."

    header = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n{'='*60}\n\n"
    (folder / filename).write_text(header + content, encoding="utf-8")
    return f"Saved to: {folder / filename}"

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Default: stdio transport for Claude Desktop.
    # To use as an HTTP server, change to: mcp.run(transport="streamable-http")
    mcp.run(transport="stdio")
