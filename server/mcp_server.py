from mcp.server.fastmcp import FastMCP

# import your existing logic
from server.resources.critiques import *
from server.resources.futures import *
from server.tools.submit_architecture import submit_architecture
# from server.tools.simulate_future import simulate_future
from server.tools.declare_tradeoff import declare_tradeoff
from server.resources.roots import load_roots, format_roots_for_prompt
# from server.tools.evaluate_architecture import evaluate_architecture
from mcp.server.fastmcp import Context
from mcp.types import SamplingMessage, TextContent
from pydantic import BaseModel, Field
from typing import Literal
import json
from pathlib import Path
from server.state.store import REVIEW_STORE
mcp = FastMCP("SpeculativeSystemDesigner")

ROOT_PATH = Path(__file__).parent.parent

FUTURES = load_futures()

# class TradeoffSelection(BaseModel):
#     selected_option: Literal["A", "B", "C"] = Field(
#         description="Select which tradeoff option you accept"
#     )

class TradeoffSelection(BaseModel):
    selected_option: str = Field(
        description="Enter the ID of the tradeoff option you accept (e.g., A, B, C)"
    )

# ---------- RESOURCES ----------
@mcp.resource("roots://governance")
def roots_resource():
    return load_roots()

@mcp.resource("roots://futures")
def futures_resource():
    return load_futures()


# ---------- TOOLS ----------
@mcp.tool()
async def generate_architecture_tool(ctx: Context, problem_statement: str):
    
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
                    )
                ),
            )
        ],
        max_tokens=800,
    )
    architecture_text = result.content.text
    architecture = submit_architecture(architecture_text)

    return {
        "status": "architecture_generated",
        "architecture_id": architecture["architecture_id"],
        "architecture_text":architecture_text
    }


@mcp.tool()
async def propose_tradeoff_tool(ctx: Context, architecture_id: str, critique_id: str, critique_summary: str):

    # Step 1: Generate structured tradeoff options
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
                        '    {"id": "B", ...},\n'
                        '    {"id": "C", ...}\n'
                        "  ]\n"
                        "}\n\n"
                        f"Critique:\n{critique_summary}"
                    )
                ),
            )
        ],
        max_tokens=400,
    )
    raw_text = result.content.text
    
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```json")[1].strip("```")
    print(raw_text)

    parsed = json.loads(raw_text)
    options = parsed["options"]
    print("OPTIONSSSSS",options)
    print("SCHEMAAAAA",TradeoffSelection.model_json_schema())
    options_text = "\n\n".join(
        f"{o['id']}:\n"
        f"  Statement: {o['statement']}\n"
        f"  Sacrifice: {o['sacrifice']}\n"
        f"  Benefit: {o['benefit']}\n"
        for o in options
        )

    # Step 2: Ask host to choose
    elicitation = await ctx.elicit(
        message=f"Select which tradeoff you are willing to accept.\n {options_text}",
        schema=TradeoffSelection,
    )

    if elicitation.action != "accept" or not elicitation.data:
        return {"status": "cancelled"}
    
    selected_id = elicitation.data.selected_option.strip().upper()
    print("SELECTEDDDDD",selected_id)
    valid_ids = {o["id"] for o in options}

    if selected_id not in valid_ids:
        return {
            "status": "error",
            "message": f"Invalid selection. Must be one of {valid_ids}"
        }

    selected_option = next(o for o in options if o["id"] == selected_id)

    # selected_id = elicitation.data.selected_option
    # selected_option = next(o for o in options if o["id"] == selected_id)

    # Step 3: Record tradeoff
    declare_tradeoff(architecture_id, critique_id, selected_option["statement"])

    return {
        "status": "tradeoff_declared",
        "selected": selected_option
    }


# @mcp.tool()
# def require_sacrifice_tool():
#     unresolved = unresolved_critiques()

#     if not unresolved:
#         return {"status": "ok", "message": "All futures satisfied"}

#     return {
#         "status": "blocked",
#         "message": "Unresolved futures detected",
#         "futures": [
#             {"critique_id": c.id, "future": c.future, "summary": c.summary}
#             for c in unresolved
#         ]
#     }


@mcp.tool()
def submit_architecture_tool(description: str):
    return submit_architecture(description)

@mcp.tool()
async def simulate_future_tool(ctx: Context,
                               architecture_id: str,
                               future_id: str):

    review = REVIEW_STORE.get(architecture_id)
    # print(review)
    if not review:
        return {"status": "error", "reason": "Unknown architecture"}

    architecture_text = review["initial_architecture"]

    future = FUTURES[future_id]
    review_prompt = future["review_prompt"]

    # --------------------------
    # MCP SAMPLING HERE
    # --------------------------
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

    raw_text = result.content.text
    # print(raw_text)

    if raw_text.startswith("```"):
        raw_text = raw_text.split("```json")[1].strip("```")

    parsed = json.loads(raw_text)
    # print(parsed)

    critique = Critique(
        id=str(uuid4()),
        future=future_id,
        summary=parsed["summary"],
        risks=parsed["risks"],
        required_tradeoff="Unresolved",
    )

    save_critique(critique)

    review["critiques"].append(critique.id)
    critique_summary = critique.model_dump()

    return {
        "status": "critique_generated",
        "critique": critique_summary,
    }


@mcp.tool()
async def evaluate_architecture_tool(ctx: Context,
                                     architecture_id: str):
    # Step 1: Simulate futures and identify critiques
    print("\n--- EVALUATING FUTURES ---")
    critiques = []
    for future_id in FUTURES.keys():
        # print(future_id)
        result = await simulate_future_tool(
            ctx,
            architecture_id=architecture_id,
            future_id=future_id,
        )
        critiques.append(result["critique"])
    
    # Step 2: For each Critique, propose tradeoff and declare it
    for critique in critiques:
        critique_id = critique["id"]
        critique_summary = critique["summary"]

        resolution = await propose_tradeoff_tool(
            ctx,
            architecture_id,
            critique_id, 
            critique_summary)
        
    # Step 3: Using the critiques and tradeoffs selected, generate final architecture
    final_architecture = await finalize_architecture_tool(
            ctx,
            architecture_id
        )


    return {
        "status": "evaluation_complete",
        "final_architecture": final_architecture,
    }


# @mcp.tool()
# def declare_tradeoff_tool(architecture_id: str, critique_id: str, tradeoff: str):
#     return declare_tradeoff(architecture_id, critique_id, tradeoff)



@mcp.tool()
async def finalize_architecture_tool(ctx: Context, architecture_id: str):

    review = REVIEW_STORE.get(architecture_id)
    if not review:
        return {"status": "error", "reason": "Unknown architecture"}

    initial_arch = review["initial_architecture"]
    tradeoffs = review["tradeoffs"]

    if not tradeoffs:
        return {
            "status": "error",
            "reason": "No tradeoffs declared"
        }

    tradeoff_text = "\n".join(
        [f"- {t['statement']}" for t in tradeoffs]
    )

    result = await ctx.session.create_message(
        messages=[
            SamplingMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=(
                        "You previously proposed this architecture:\n\n"
                        f"{initial_arch}\n\n"
                        "The following tradeoffs have been explicitly accepted:\n\n"
                        f"{tradeoff_text}\n\n"
                        "Produce a final architecture that clearly and concretely reflects these tradeoffs.\n"
                        "Be technical and specific. Keep the complete architecture conscise within 10 sentences."
                    )
                ),
            )
        ],
        max_tokens=600,
    )

    final_arch = result.content.text
    review["final_architecture"] = final_arch

    return {
        "status": "finalized",
        "final_architecture": final_arch
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")

