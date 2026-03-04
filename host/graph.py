"""
LangGraph graph definition.

Flow (see graph_flow.svg):

    generate
        └─► draw_initial (Excalidraw)
                ├─[run_evaluation=False]─► END
                └─[run_evaluation=True]──► simulate_future ◄─┐
                                               └─► propose_tradeoff
                                                       ├─[more futures]──────┘
                                                       └─[done]──► finalize
                                                                       └─► draw_final (Excalidraw)
                                                                               └─► END
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from mcp import ClientSession

from .state import DesignState
from .nodes import (
    fetch_future_ids,
    generate_architecture_node,
    draw_diagram_node,
    simulate_future_node,
    propose_tradeoff_node,
    finalize_architecture_node,
)


async def build_graph(ssd_session: ClientSession, ex_session: ClientSession):
    """
    Fetches future IDs from the SSD server, then compiles the LangGraph graph.

    Both sessions are captured in node closures so each node keeps the
    clean (state) -> dict signature LangGraph requires.
    """

    # ── Fetch futures once at build time ──────────────────────────────────────
    future_ids = await fetch_future_ids(ssd_session)
    print(f"[graph] Futures loaded from server: {future_ids}")

    # ── Node closures (bind sessions + future_ids) ────────────────────────────
    async def _generate(state: DesignState) -> dict:
        return await generate_architecture_node(state, ssd_session)

    async def _draw_initial(state: DesignState) -> dict:
        return await draw_diagram_node(state, ex_session, phase="initial")

    async def _simulate(state: DesignState) -> dict:
        return await simulate_future_node(state, ssd_session, future_ids)

    async def _tradeoff(state: DesignState) -> dict:
        return await propose_tradeoff_node(state, ssd_session)

    async def _finalize(state: DesignState) -> dict:
        return await finalize_architecture_node(state, ssd_session)

    async def _draw_final(state: DesignState) -> dict:
        return await draw_diagram_node(state, ex_session, phase="final")

    # ── Routing functions ─────────────────────────────────────────────────────

    def route_after_draw_initial(state: DesignState) -> str:
        """Branch based on the run_evaluation flag supplied by the caller."""
        return "simulate_future" if state["run_evaluation"] else END

    def route_after_tradeoff(state: DesignState) -> str:
        """Loop back to simulate_future until all futures are processed."""
        if state["current_future_index"] < len(future_ids):
            return "simulate_future"
        return "finalize"

    # ── Build graph ───────────────────────────────────────────────────────────
    g = StateGraph(DesignState)

    g.add_node("generate",        _generate)
    g.add_node("draw_initial",    _draw_initial)
    g.add_node("simulate_future", _simulate)
    g.add_node("propose_tradeoff",_tradeoff)
    g.add_node("finalize",        _finalize)
    g.add_node("draw_final",      _draw_final)

    g.set_entry_point("generate")

    g.add_edge("generate",     "draw_initial")

    g.add_conditional_edges(
        "draw_initial",
        route_after_draw_initial,
        {
            "simulate_future": "simulate_future",
            END:                END,
        },
    )

    g.add_edge("simulate_future",  "propose_tradeoff")

    g.add_conditional_edges(
        "propose_tradeoff",
        route_after_tradeoff,
        {
            "simulate_future": "simulate_future",
            "finalize":        "finalize",
        },
    )

    g.add_edge("finalize",    "draw_final")
    g.add_edge("draw_final",  END)

    # MemorySaver enables interrupt() for human-in-the-loop elicitation
    return g.compile(checkpointer=MemorySaver())
