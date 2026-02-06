import asyncio
from openai import OpenAI
import json
# from mcp.client.stdio import stdio_client
# from mcp.client.websocket import websocket_client
from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession, StdioServerParameters, types
from dotenv import load_dotenv
import anyio
load_dotenv(override=True)
import os
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
from mcp.shared.context import RequestContext
# Optional: create a sampling callback

async def handle_sampling_message(
    context: RequestContext[ClientSession, None], params: types.CreateMessageRequestParams
) -> types.CreateMessageResult:
    # print(f"Sampling request: {params.messages}")
    messages = ""
    for message in params.messages:
        messages += message.content.text
    llm_response = client.responses.create(
        model="gpt-4.1-mini",
        input=messages,
    )
    # print(f"Sampling request: {messages}")
    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(
            type="text",
            text=llm_response.output_text,
        ),
        model="gpt-4.1-mini",
        stopReason="endTurn",
    )
    

async def run():

    user_problem = """
    Design a backend system that ingests events asynchronously,
    processes them, and exposes analytics APIs for customers in 4 to 5 sentenses.
    """

    llm_response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"Propose a system architecture:\n{user_problem}",
    )

    architecture_text = llm_response.output_text
    print("\nLLM ARCHITECTURE:\n", architecture_text)

    # async with stdio_client(server=(proc.stdin, proc.stdout)) as (read, write):
    async with streamable_http_client("http://127.0.0.1:8000/mcp") as (read_stream, write_stream, sess_id):
        async with ClientSession(read_stream, write_stream,sampling_callback=handle_sampling_message) as session:
            await session.initialize()

            # Submit architecture
            submission = await session.call_tool(
                "submit_architecture_tool",
                {"description": architecture_text},
            )
            print("\nSUBMISSION:", submission)

            # Simulate scaling future
            future = await session.call_tool(
                "simulate_scaling_future_tool",
                {"description": architecture_text},
            )
            future_result = json.loads(future.content[0].text)
            
            print("\nFUTURE:", future_result)
            
            critique_text = future_result["critique"]["summary"]

            # # Ask server to sample tradeoff
            tradeoff = await session.call_tool(
                "propose_tradeoff_tool",
                {"critique_summary": critique_text}
            )

            print("\nTRADEOFF:", tradeoff.content[0].text)



asyncio.run(run())
