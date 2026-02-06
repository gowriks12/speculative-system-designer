from mcp.server.fastmcp import FastMCP

# import your existing logic
from server.tools.submit_architecture import submit_architecture
from server.tools.simulate_future import simulate_scaling_future
from server.tools.declare_tradeoff import declare_tradeoff
from server.resources.roots import load_roots
from mcp.server.fastmcp import Context
from mcp.types import SamplingMessage, TextContent
mcp = FastMCP("SpeculativeSystemDesigner")

# ---------- RESOURCES ----------
@mcp.resource("roots://governance")
def roots_resource():
    return load_roots()


# ---------- TOOLS ----------
@mcp.tool()
async def propose_tradeoff_tool(ctx: Context, critique_summary: str):
    """
    Requests the client LLM to propose a tradeoff statement.
    This uses MCP sampling.
    """

    result=await ctx.session.create_message(
        messages=[
            SamplingMessage(role="user", content=TextContent(type="text", text="You are an experienced system architect proposing explicit engineering tradeoffs.")),
            SamplingMessage(role="user", content=TextContent(type="text", text=f"Based on the following critique, propose a concise architectural tradeoff:\n{critique_summary}"))
        ],
        max_tokens=200
    )

    # result = await ctx.sample(
    #     messages=[
    #         {
    #             "role": "system",
    #             "content": "You are an experienced system architect proposing explicit engineering tradeoffs."
    #         },
    #         {
    #             "role": "user",
    #             "content": f"Based on the following critique, propose a concise architectural tradeoff:\n{critique_summary}"
    #         }
    #     ],
    #     max_tokens=200,
    # )

    tradeoff_text = result.content.text

    return {
        "status": "tradeoff_proposed",
        "tradeoff": tradeoff_text
    }

@mcp.tool()
def submit_architecture_tool(description: str):
    return submit_architecture(description)


@mcp.tool()
def simulate_scaling_future_tool(description: str):
    return simulate_scaling_future(description)


@mcp.tool()
def declare_tradeoff_tool(critique_id: str, tradeoff: str):
    return declare_tradeoff(critique_id, tradeoff)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")

