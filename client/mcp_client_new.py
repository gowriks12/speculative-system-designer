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
import json
from pathlib import Path

FUTURES_PATH = Path("data/futures.json")

def load_futures():
    with open(FUTURES_PATH) as f:
        return json.load(f)
    

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

    # architecture_text = llm_response.output_text
    # print("\nLLM ARCHITECTURE:\n", architecture_text)
    architecture_text = """ Design a scalable backend system where events are ingested asynchronously via a message queue (e.g., Kafka) to decouple producers from consumers and ensure high throughput. Event data is then processed in real-time or batch using a stream processing framework (e.g., Apache Flink or Spark Streaming) to transform, aggregate, and enrich the events. Processed data is stored in a fast, query-optimized database (e.g., a time-series or columnar store like ClickHouse or Druid). Finally, a RESTful or GraphQL analytics API layer exposes aggregated insights and customizable metrics to customers, supported by caching (e.g., Redis) to ensure low-latency response times. The system can horizontally scale at each layer to handle growing event volumes and query loads."""
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

            evaluation = await session.call_tool(
                "evaluate_architecture_tool",
                {"description": architecture_text}
            )
            print("Evaluation result ",evaluation.content[0].text)
            raw_eval_res = evaluation.content[0].text
            if raw_eval_res.startswith("```"):
                raw_eval_res = raw_eval_res.split("```json")[1].strip("```")
            evaluation_result = json.loads(raw_eval_res)

            critiques = evaluation_result["critiques"]

            for critique in critiques:
                critique_id = critique["id"]
                summary = critique["summary"]

                print(f"\n--- Future: {critique['future']} ---")
                print("CRITIQUE:", summary)

                tradeoff = await session.call_tool(
                    "propose_tradeoff_tool",
                    {"critique_summary": summary}
                )

                tradeoff_text = tradeoff.content[0].text

                resolution = await session.call_tool(
                    "declare_tradeoff_tool",
                    {
                        "critique_id": critique_id,
                        "tradeoff": tradeoff_text
                    }
                )

                print("RESOLUTION:", resolution.content[0].text)

                final = await session.call_tool("require_sacrifice_tool", {})
                print("\nFINAL STATUS:", final.content[0].text)


asyncio.run(run())
