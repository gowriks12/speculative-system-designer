"""
Entry point for the LangGraph + MCP host.

Usage:
    python -m host.run                 # run with future evaluation
    python -m host.run --no-eval       # generate + draw only, skip futures

Environment variables (set in .env):
    OPENAI_API_KEY      — required
    SERVER_PYTHON       — path to the venv Python that runs mcp_server.py
                          defaults to .venv/Scripts/python.exe (Windows)
                                   or .venv/bin/python          (Unix)
    SERVER_MODULE       — Python module path, default: server.mcp_server
    ELICITATION_MODE    — "llm" (default, fully agentic) | "human" (interrupt)
    LLM_MODEL           — OpenAI model name, default: gpt-4o-mini
    EXCALIDRAW_MCP_URL  — Excalidraw MCP server URL
                          default: https://mcp.excalidraw.com/mcp

Human-in-the-loop mode
-----------------------
Set ELICITATION_MODE=human. The graph will pause at each tradeoff via
interrupt(). Resume by calling:

    from langgraph.types import Command
    await graph.ainvoke(Command(resume="B"), config=config)
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from .handlers import sampling_handler, elicitation_handler
from .graph import build_graph

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────────

def _default_python() -> str:
    if sys.platform == "win32":
        candidate = Path(".venv/Scripts/python.exe")
    else:
        candidate = Path(".venv/bin/python")
    return str(candidate) if candidate.exists() else sys.executable


SERVER_PYTHON      = os.getenv("SERVER_PYTHON", _default_python())
SERVER_MODULE      = os.getenv("SERVER_MODULE", "server.mcp_server")
EXCALIDRAW_MCP_URL = os.getenv("EXCALIDRAW_MCP_URL", "https://mcp.excalidraw.com/mcp")
ELICITATION_MODE   = os.getenv("ELICITATION_MODE", "llm")

PROBLEM_STATEMENT = """
Design a backend system that ingests events asynchronously,
processes them, and exposes analytics APIs for customers.
"""

# ── Entry point ───────────────────────────────────────────────────────────────

async def main(run_evaluation: bool = True):
    print(f"[run] SSD server  : {SERVER_PYTHON} -m {SERVER_MODULE}")
    print(f"[run] Excalidraw  : {EXCALIDRAW_MCP_URL}")
    print(f"[run] Evaluation  : {'enabled' if run_evaluation else 'skipped'}")
    print(f"[run] Elicitation : {ELICITATION_MODE}\n")

    ssd_params = StdioServerParameters(
        command=SERVER_PYTHON,
        args=["-m", SERVER_MODULE],
    )

    # Open both MCP connections — SSD (stdio) and Excalidraw (HTTP)
    async with stdio_client(ssd_params) as (ssd_read, ssd_write):
        async with streamable_http_client(EXCALIDRAW_MCP_URL) as (ex_read, ex_write, _):
            async with ClientSession(
                ssd_read, ssd_write,
                sampling_callback=sampling_handler,
                elicitation_callback=elicitation_handler,
            ) as ssd_session:
                async with ClientSession(ex_read, ex_write) as ex_session:

                    await ssd_session.initialize()
                    await ex_session.initialize()

                    graph  = await build_graph(ssd_session, ex_session)
                    config = {"configurable": {"thread_id": "design-session-1"}}

                    initial_state = {
                        "problem_statement":    PROBLEM_STATEMENT.strip(),
                        "run_evaluation":       run_evaluation,
                        "architecture_id":      None,
                        "architecture_text":    None,
                        "critiques":            [],
                        "tradeoffs":            [],
                        "final_architecture":   None,
                        "current_future_index": 0,
                        "future_ids":           [],
                        "initial_diagram_url":  None,
                        "final_diagram_url":    None,
                    }

                    result = await graph.ainvoke(initial_state, config=config)

                    # ── Summary ────────────────────────────────────────────
                    print("\n\n========================================")
                    print("DESIGN SESSION COMPLETE")
                    print("========================================")
                    print(f"Architecture ID      : {result['architecture_id']}")
                    print(f"Initial diagram      : {result.get('initial_diagram_url', 'n/a')}")

                    if run_evaluation:
                        print(f"Futures simulated    : {len(result['critiques'])}")
                        print(f"Tradeoffs declared   : {len(result['tradeoffs'])}")
                        print(f"Final diagram        : {result.get('final_diagram_url', 'n/a')}")
                        print("\nFINAL ARCHITECTURE:\n")
                        print(result["final_architecture"])
                    else:
                        print("\nINITIAL ARCHITECTURE:\n")
                        print(result["architecture_text"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Speculative System Designer — LangGraph host")
    parser.add_argument(
        "--no-eval",
        action="store_true",
        help="Skip future simulation; generate architecture and draw diagram only",
    )
    args = parser.parse_args()

    asyncio.run(main(run_evaluation=not args.no_eval))
