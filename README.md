# Speculative System Designer

> An MCP server + LangGraph host that generates, stress-tests, and governs software architectures through structured futures, explicit tradeoffs, and Excalidraw diagrams.

---

## What Is This?

Most architecture review processes happen too late and too politely. Teams propose a system, debate it briefly, then ship with unresolved assumptions baked in.

**Speculative System Designer** flips that. It forces three things that are usually skipped:

1. **Non-negotiable constraints** declared *before* design begins — called *Roots*
2. **Pessimistic futures** simulated *against* the design after it is proposed
3. **Explicit tradeoffs** accepted *on the record* before a final architecture is issued

The project is split into two independent layers:

| Layer | What it does |
|---|---|
| **Server** (`server/mcp_server.py`) | FastMCP server — exposes tools, enforces governance rules, manages state |
| **Host / Client** (`host/`) | LangGraph orchestration — drives the server tools through a stateful graph, connects Excalidraw |

---

## Repository Layout

```
SpeculativeSystemDesigner/
├── data/
│   ├── roots.json              ← Non-negotiable architectural constraints
│   └── futures.json            ← Pessimistic stress-test scenarios
│
├── server/
│   ├── mcp_server.py           ← FastMCP entry point (all tools registered here)
│   ├── architectures.py        ← Architecture model + submit_architecture factory
│   ├── critiques.py            ← Critique model, CRITIQUE_STORE, helpers
│   ├── futures.py              ← Loads futures.json
│   ├── roots.py                ← Loads roots.json + prompt formatter
│   ├── store.py                ← In-memory REVIEW_STORE
│   ├── declare_tradeoff.py     ← Records an accepted tradeoff
│   ├── TOOLS.md                ← Tool-by-tool API reference
│   └── CONCEPTS.md             ← Deep-dive into Roots, Futures, Tradeoffs
│
├── host/
│   ├── __init__.py
│   ├── state.py                ← DesignState TypedDict
│   ├── handlers.py             ← MCP sampling + elicitation callbacks
│   ├── nodes.py                ← LangGraph node implementations
│   ├── graph.py                ← Graph definition and routing logic
│   └── run.py                  ← CLI entry point
│
├── graph_flow.svg              ← Visual graph flow reference
├── requirements.txt
├── pyproject.toml
├── .env.example
└── README.md
```

---

## Key Concepts

| Concept | Description |
|---|---|
| **Root** | A non-negotiable architectural constraint (e.g. "must be operable by ≤ 6 engineers"). Violations block approval. Defined in `data/roots.json`. |
| **Future** | A pessimistic scenario the system might have to operate in — scaling 10x, security abuse, regulatory change. Defined in `data/futures.json`. |
| **Critique** | Structured LLM feedback produced by simulating a Future against an architecture. Contains a `summary` and up to 3 `risks`. |
| **Tradeoff** | An explicit, human-accepted compromise that resolves a Critique. Must be declared before the final architecture is issued. |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   LangGraph Host (host/)                    │
│   run.py ──► graph.py ──► nodes.py                          │
│                  │                                          │
│   handlers.py (sampling + elicitation callbacks)            │
└─────────────┬───────────────────┬──────────────────────────┘
              │ MCP stdio         │ MCP streamable-http
              ▼                   ▼
┌─────────────────────┐  ┌────────────────────────┐
│  SSD MCP Server     │  │  Excalidraw MCP Server  │
│  (mcp_server.py)    │  │  mcp.excalidraw.com/mcp │
│                     │  └────────────────────────┘
│  Tools              │
│  ├─ generate_arch   │
│  ├─ simulate_future │   Resources
│  ├─ propose_trdoff  │   ├─ roots://governance
│  ├─ finalize_arch   │   └─ roots://futures
│  ├─ evaluate_arch   │
│  ├─ list_roots      │   State (in-memory)
│  ├─ list_futures    │   └─ REVIEW_STORE + CRITIQUE_STORE
│  └─ write_arch      │
│                     │
│  data/              │
│  ├─ roots.json      │
│  └─ futures.json    │
└─────────────────────┘
```

**Authority belongs to the server.** Governance prompts — root constraints, future scenarios, critique structure — all live inside the MCP server. The client cannot bypass them.

**Creativity belongs to the client.** The client LLM handles open-ended synthesis: proposing architectures, generating tradeoff options, writing the final document.

---

## Server Features

### Tools

The server exposes eight tools over MCP. Five are async (they use MCP Sampling to delegate LLM calls back to the client), and three are synchronous utilities.

#### `generate_architecture_tool` *(async)*
Generates a system architecture that satisfies all Roots defined in `data/roots.json`. It uses **MCP Sampling** to send the prompt — including all root constraints verbatim — to the client LLM. The result is immediately saved to `REVIEW_STORE` and an `architecture_id` is returned for all subsequent tool calls.

#### `simulate_future_tool` *(async)*
Stress-tests a saved architecture against a single future scenario. Sends the future's `review_prompt` + the architecture text to the client LLM via Sampling, and expects a JSON response with `summary` (string) and `risks` (list). Creates and stores a `Critique` object.

#### `propose_tradeoff_tool` *(async)*
Two-phase tool that resolves a Critique:
1. **Sampling phase** — the LLM generates exactly three tradeoff options (A, B, C) each with a `statement`, `sacrifice`, and `benefit`.
2. **Elicitation phase** — the options are presented to the human via **MCP Elicitation**. The human picks one; the server records it via `declare_tradeoff` and marks the Critique resolved.

The server never lets the LLM choose the tradeoff — that decision always belongs to the human.

#### `evaluate_architecture_tool` *(async — orchestrator)*
The high-level entry point for a full evaluation run. Internally calls `simulate_future_tool` for every future in `data/futures.json`, then `propose_tradeoff_tool` for every resulting Critique, then `finalize_architecture_tool`. The user is prompted (via Elicitation) once per future to select a tradeoff.

#### `finalize_architecture_tool` *(async)*
Produces the final governed architecture incorporating all accepted tradeoffs. Refuses to execute if no tradeoffs have been declared — the server enforces that every Critique must be resolved first. Uses Sampling to delegate synthesis to the client LLM.

#### `list_roots_scope` *(sync)*
Returns a list of the root constraint IDs currently loaded from `data/roots.json`.

#### `list_futures_scope` *(sync)*
Returns a list of the future IDs currently loaded from `data/futures.json`. Used by the LangGraph host at startup to discover futures dynamically without hardcoding.

#### `write_architecture` *(sync)*
Writes an architecture document (initial, simulated future, or final) to `architectures/<use_case>/` on disk.

### Resources

The server exposes two MCP Resources that any client can read directly:

| URI | Contents |
|---|---|
| `roots://governance` | Full `data/roots.json` |
| `roots://futures` | Full `data/futures.json` |

### State Management

All runtime state lives in two in-memory dicts (reset on server restart):

| Store | Location | Contents |
|---|---|---|
| `REVIEW_STORE` | `store.py` | One entry per architecture: initial text, tradeoff list, critique ID list, final text |
| `CRITIQUE_STORE` | `critiques.py` | One entry per `Critique` object, keyed by UUID |

### Default Roots (`data/roots.json`)

| Root ID | Constraint |
|---|---|
| `team_constraints` | System must be buildable and operable by ≤ 6 engineers. |
| `cost_discipline` | Baseline infrastructure costs must be predictable and defensible to non-technical stakeholders. |
| `operational_observability` | System must be diagnosable without ad-hoc instrumentation in production. |
| `reversibility` | Major architectural decisions must be reversible without a full rewrite. |

### Default Futures (`data/futures.json`)

| Future ID | Assumption | Stance |
|---|---|---|
| `scaling` | Traffic and data volume increase 10x within 18 months | Pessimistic |
| `security_abuse` | Attackers are competent; internal misconfigurations will occur | Adversarial |
| `regulatory_compliance` | New compliance requirements arrive with short notice after the system ships | Literal |

---

## Host / Client (LangGraph)

The `host/` package is a LangGraph orchestration layer that drives the SSD server tools through a stateful directed graph. It maintains two MCP sessions simultaneously — one to the SSD server (stdio) and one to the Excalidraw MCP server (HTTP).

### Graph Flow

```
generate
  └─► draw_initial (Excalidraw)
          │
          ├─[--no-eval / run_evaluation=False]──────────────► END
          │
          └─[run_evaluation=True]──► simulate_future ◄────────┐
                                          │                    │
                                          ▼                    │ (more futures)
                                    propose_tradeoff           │
                                          │                    │
                                          ├─[more futures]─────┘
                                          │
                                          └─[all done]──► finalize
                                                              │
                                                              ▼
                                                        draw_final (Excalidraw)
                                                              │
                                                              ▼
                                                             END
```

See `graph_flow.svg` for a visual version.

### Nodes (`host/nodes.py`)

| Node | MCP Tool Called | What It Does |
|---|---|---|
| `generate` | `generate_architecture_tool` | Generates the initial architecture; seeds `architecture_id`, `architecture_text`, resets loop index |
| `draw_initial` | Excalidraw `create_drawing` | Converts architecture text → Excalidraw elements JSON (via LLM) → creates diagram, stores `initial_diagram_url` |
| `simulate_future` | `simulate_future_tool` | Simulates the next future in the list; appends Critique to state, increments `current_future_index` |
| `propose_tradeoff` | `propose_tradeoff_tool` | Proposes options for the latest Critique; the elicitation callback resolves the choice; appends to `tradeoffs` |
| `finalize` | `finalize_architecture_tool` | Synthesizes the final architecture from the initial design + all declared tradeoffs |
| `draw_final` | Excalidraw `create_drawing` | Same as `draw_initial` but for the final architecture; stores `final_diagram_url` |

### Routing Logic (`host/graph.py`)

Two conditional edges control the flow:

- **After `draw_initial`**: branches on `state["run_evaluation"]` — goes to `simulate_future` if `True`, otherwise ends immediately. Controlled by the `--no-eval` CLI flag.
- **After `propose_tradeoff`**: loops back to `simulate_future` while `current_future_index < len(future_ids)`, then proceeds to `finalize` when all futures are exhausted.

Future IDs are fetched dynamically from the server via `list_futures_scope` at graph build time — the host never hardcodes future names.

### State (`host/state.py`)

```python
class DesignState(TypedDict):
    problem_statement: str
    run_evaluation: bool            # True = simulate futures, False = generate + draw only
    architecture_id: Optional[str]
    architecture_text: Optional[str]
    critiques: List[dict]           # [{id, future, summary, risks, ...}]
    tradeoffs: List[dict]           # [{critique_id, selected, ...}]
    final_architecture: Optional[str]
    current_future_index: int       # loop counter through futures
    future_ids: List[str]
    initial_diagram_url: Optional[str]
    final_diagram_url: Optional[str]
```

### Sampling & Elicitation Handlers (`host/handlers.py`)

The host registers two callbacks with the MCP `ClientSession`:

**`sampling_handler`** — called whenever the SSD server invokes `ctx.session.create_message`. Forwards the message to the configured OpenAI model and returns the result. This is how the server delegates all LLM work to the client without needing API keys of its own.

**`elicitation_handler`** — called whenever the SSD server invokes `ctx.elicit` (currently in `propose_tradeoff_tool`). Behaviour depends on `ELICITATION_MODE`:

| Mode | Behaviour |
|---|---|
| `llm` (default) | An LLM reads the A/B/C options and selects the most pragmatic one automatically |
| `human` | LangGraph `interrupt()` pauses the graph; a human resumes it with `Command(resume="B")` |

### Excalidraw Integration

The host connects to the Excalidraw MCP server at `https://mcp.excalidraw.com/mcp` (overridable via `EXCALIDRAW_MCP_URL`). For each draw node it:

1. Calls an LLM (gpt-4o-mini) to translate architecture prose into a valid Excalidraw elements JSON array (rectangles for services, arrows for data flows).
2. Calls the Excalidraw `create_drawing` tool with those elements.
3. Stores the returned shareable URL in `DesignState`.

Two diagrams are produced per full run — initial and final — both URLs are printed at the end of the session.

---

## Setup

### Prerequisites

- Python 3.11+
- [Claude Desktop](https://claude.ai/download) or any MCP-compatible client
- An OpenAI API key (for the LangGraph host)

### Install

```bash
git clone https://github.com/yourname/speculative-system-designer
cd speculative-system-designer

python -m venv .venv
# Windows
.venv\Scripts\activate
# Unix / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Edit .env — set OPENAI_API_KEY at minimum
```

Key environment variables:

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Required for the LangGraph host |
| `SERVER_PYTHON` | `.venv/Scripts/python.exe` (Win) / `.venv/bin/python` (Unix) | Path to the venv Python |
| `SERVER_MODULE` | `server.mcp_server` | Python module path for the MCP server |
| `ELICITATION_MODE` | `llm` | `llm` for fully agentic, `human` to pause at each tradeoff |
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI model for sampling and elicitation |
| `EXCALIDRAW_MCP_URL` | `https://mcp.excalidraw.com/mcp` | Excalidraw MCP server URL |

---

## Running

### Option A — LangGraph Host (full agentic run)

```bash
# Full run: generate → evaluate all futures → finalize → draw both diagrams
python -m host.run

# Skip evaluation: generate + draw initial diagram only
python -m host.run --no-eval
```

End of run output:
```
========================================
DESIGN SESSION COMPLETE
========================================
Architecture ID      : <uuid>
Initial diagram      : https://excalidraw.com/#...
Futures simulated    : 3
Tradeoffs declared   : 3
Final diagram        : https://excalidraw.com/#...

FINAL ARCHITECTURE:
...
```

### Option B — Claude Desktop

Add the server to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "speculative-system-designer": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/speculative-system-designer/server/mcp_server.py"],
      "cwd": "/path/to/speculative-system-designer",
      "env": {
        "PYTHONPATH": "/path/to/speculative-system-designer"
      }
    }
  }
}
```

Restart Claude Desktop and run:

```
Design a backend system that ingests events asynchronously, processes them
in near-real-time, and exposes analytics APIs for customers. Team has 4 engineers.
```

Claude will call `generate_architecture_tool`, then `evaluate_architecture_tool`, presenting tradeoff choices along the way before delivering a finalized, self-aware architecture.

### Option C — HTTP Transport

```python
# In server/mcp_server.py, change the last line to:
mcp.run(transport="streamable-http")
```

```bash
python -m server.mcp_server
# Server available at http://127.0.0.1:8000/mcp
```

---

## Human-in-the-Loop Mode

Set `ELICITATION_MODE=human` in `.env`. The graph pauses at each `propose_tradeoff_tool` call via LangGraph `interrupt()`.

To resume:

```python
from langgraph.types import Command

config = {"configurable": {"thread_id": "design-session-1"}}

# First ainvoke pauses at the first tradeoff
result = await graph.ainvoke(initial_state, config=config)

# Resume with the human's choice
result = await graph.ainvoke(Command(resume="B"), config=config)
```

---

## Customising Roots and Futures

Both files are plain JSON — no code changes required.

### Adding a Root (`data/roots.json`)

```json
{
  "your_root_id": {
    "id": "your_root_id",
    "statement": "The constraint in plain language.",
    "rationale": "Why this constraint exists.",
    "violation_examples": [
      "concrete example of something that breaks this rule"
    ]
  }
}
```

Roots are injected into the next `generate_architecture_tool` call automatically.

### Adding a Future (`data/futures.json`)

```json
{
  "your_future_id": {
    "id": "your_future_id",
    "description": "What this scenario assumes.",
    "assumption": "The specific pessimistic assumption.",
    "stance": "pessimistic | adversarial | literal",
    "review_prompt": "You are a [role]. Given this architecture... Respond ONLY in JSON: {\"summary\": \"...\", \"risks\": [\"...\"]}"
  }
}
```

The `review_prompt` **must** instruct the model to return JSON with `summary` (string) and `risks` (array of strings). The LangGraph host picks up new futures automatically via `list_futures_scope` at graph build time.

---

## Swapping the LLM (Host)

The host uses OpenAI by default. To switch to Anthropic, edit `host/handlers.py` and `host/nodes.py`:

```python
from anthropic import AsyncAnthropic
_client = AsyncAnthropic()   # reads ANTHROPIC_API_KEY

# In sampling_handler, replace the openai call with:
response = await _client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=800,
    messages=messages,
)
text = response.content[0].text
```

---

## MCP Features Used

| Feature | Where |
|---|---|
| **Tools** | All `@mcp.tool()` functions in `mcp_server.py` |
| **Resources** | `roots://governance`, `roots://futures` |
| **Sampling** (`ctx.session.create_message`) | Architecture generation, future simulation, tradeoff option generation, finalization — server delegates LLM calls back to the client |
| **Elicitation** (`ctx.elicit`) | `propose_tradeoff_tool` — server presents choices to the human and waits for a selection |

---

## Design Principles

**Authority belongs to the server.** Governance prompts live inside the MCP server. The client cannot skip or alter them.

**Creativity belongs to the client.** The client LLM handles open-ended synthesis.

**Tradeoffs are first-class artifacts.** Every accepted tradeoff is persisted in `REVIEW_STORE` and passed verbatim into the finalization prompt. Nothing is silently discarded.

**The server can say no.** `finalize_architecture_tool` refuses to produce a final architecture until every Critique is resolved.

