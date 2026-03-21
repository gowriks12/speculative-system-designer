# Speculative System Designer — MCP Server

> A FastMCP server that generates, stress-tests, and governs software architectures through non-negotiable root constraints, pessimistic futures, structured critiques, and explicit tradeoffs.

---

## What This Server Does

Most architecture tools help you build. This one helps you **question**.

The server enforces a governance pipeline in three stages:

1. **Generate** — produces an architecture that must satisfy all root constraints before it is saved
2. **Simulate** — stress-tests it against pessimistic future scenarios (scaling, security abuse, regulatory change)
3. **Finalize** — refuses to issue a final architecture until every critique has a declared tradeoff

Authority lives here. The prompts encoding judgment — root constraints, future review prompts, critique structure — are all defined on the server. A connected client cannot bypass or skip them.

---

## Directory Layout

```
server/
├── mcp_server.py           ← FastMCP entry point — all tools and resources registered here
├── architectures.py        ← Architecture model + submit_architecture factory
├── critiques.py            ← Critique model, CRITIQUE_STORE, helpers
├── futures.py              ← Loads data/futures.json
├── roots.py                ← Loads data/roots.json + prompt formatter
├── store.py                ← In-memory REVIEW_STORE
├── declare_tradeoff.py     ← Records an accepted tradeoff against a critique
├── TOOLS.md                ← Full tool-by-tool API reference
├── CONCEPTS.md             ← Deep-dive into Roots, Futures, Tradeoffs
└── data/
    ├── roots.json          ← Non-negotiable architectural constraints
    └── futures.json        ← Pessimistic stress-test scenarios
```

---

## Key Concepts

### Roots

Roots are the constitutional layer — constraints that must be satisfied before any architecture is accepted. They are injected verbatim into the generation prompt so the client LLM is forced to reason about each one explicitly.

Defined in `data/roots.json`. Four defaults are provided:

| Root ID | Constraint |
|---|---|
| `team_constraints` | System must be buildable and operable by ≤ 6 engineers |
| `cost_discipline` | Baseline infrastructure costs must be predictable and defensible to non-technical stakeholders |
| `operational_observability` | System must be diagnosable without ad-hoc instrumentation in production |
| `reversibility` | Major architectural decisions must be reversible without a full rewrite |

### Futures

A future is a pessimistic scenario the system might have to operate in. The word is deliberate — not a "risk" (which implies probability) or a "test" (which implies pass/fail). The question is: *what breaks first?*

Each future carries a `review_prompt` that is sent verbatim to the LLM via MCP Sampling. It instructs the model to act as a hostile review board and respond only in JSON.

Defined in `data/futures.json`. Three defaults are provided:

| Future ID | Assumption | Stance |
|---|---|---|
| `scaling` | Traffic and data volume increase 10x within 18 months | Pessimistic |
| `security_abuse` | Attackers are competent; internal misconfigurations will occur | Adversarial |
| `regulatory_compliance` | New compliance requirements arrive with short notice after the system ships | Literal |

### Critiques

A Critique is the structured output of running a Future against an architecture. It contains a `summary` (one-paragraph failure description) and up to three `risks`. Every Critique starts as `resolved: false` and must be resolved by a declared Tradeoff before the architecture can be finalized.

### Tradeoffs

A Tradeoff is the human's explicit on-the-record acknowledgement of a compromise. Once accepted, its statement is stored in `REVIEW_STORE` and passed verbatim into the finalization prompt — ensuring it actually shapes the final output rather than being silently ignored.

---

## Tools

The server exposes eight tools. Five are async and use **MCP Sampling** to delegate LLM calls back to the connected client. Three are synchronous utilities.

> **Note:** MCP Sampling and MCP Elicitation are advanced MCP features. They are fully supported by the LangGraph host in `host/` but are **not supported by Claude Desktop**. If you want to connect this server to Claude Desktop, see the `simple-server` branch instead.

---

### `generate_architecture_tool` *(async)*

Generates a system architecture constrained by all roots in `data/roots.json`.

Uses MCP Sampling to send the prompt — including all root constraints formatted verbatim — to the client LLM. The LLM is required to explain how its design satisfies each root before providing the final architecture text. The result is saved to `REVIEW_STORE` and an `architecture_id` is returned.

**Input**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `problem_statement` | string | ✅ | Plain-language description of the system to design |

**Output**
```json
{
  "status": "architecture_generated",
  "architecture_id": "<uuid>",
  "architecture_text": "<full architecture description>"
}
```

---

### `simulate_future_tool` *(async)*

Stress-tests a saved architecture against a single future scenario.

Sends the future's `review_prompt` and the architecture text to the client LLM via Sampling. Expects a JSON response with `summary` and `risks`. Creates and stores a `Critique` object; appends its ID to the architecture's record in `REVIEW_STORE`.

**Input**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `architecture_id` | string | ✅ | UUID from `generate_architecture_tool` |
| `future_id` | string | ✅ | Key from `data/futures.json` (e.g. `"scaling"`) |

**Output**
```json
{
  "status": "critique_generated",
  "critique": {
    "id": "<uuid>",
    "future": "scaling",
    "summary": "...",
    "risks": ["...", "...", "..."],
    "required_tradeoff": "Unresolved",
    "resolved": false
  }
}
```

---

### `propose_tradeoff_tool` *(async)*

Two-phase tool that resolves a Critique.

**Phase 1 — Sampling:** the LLM generates exactly three tradeoff options (A, B, C), each with a `statement`, `sacrifice`, and `benefit`.

**Phase 2 — Elicitation:** the options are presented to the human via MCP Elicitation. The human picks one. The server records the choice via `declare_tradeoff` and marks the Critique resolved.

The server never lets the LLM choose the tradeoff — that decision always belongs to the human.

**Input**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `architecture_id` | string | ✅ | UUID of the architecture under review |
| `critique_id` | string | ✅ | UUID of the Critique to resolve |
| `critique_summary` | string | ✅ | Human-readable summary of the problem |

**Output**
```json
{
  "status": "tradeoff_declared",
  "selected": {
    "id": "B",
    "statement": "...",
    "sacrifice": "...",
    "benefit": "..."
  }
}
```

---

### `evaluate_architecture_tool` *(async — orchestrator)*

Runs the full evaluation pipeline for a saved architecture in one call.

Internally calls `simulate_future_tool` for every future in `data/futures.json`, then `propose_tradeoff_tool` for every resulting Critique, then `finalize_architecture_tool`. The user is prompted via Elicitation once per future to select a tradeoff.

**Input**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `architecture_id` | string | ✅ | UUID from `generate_architecture_tool` |

**Output**
```json
{
  "status": "evaluation_complete",
  "final_architecture": {
    "status": "finalized",
    "final_architecture": "..."
  }
}
```

---

### `finalize_architecture_tool` *(async)*

Produces the final governed architecture incorporating all accepted tradeoffs.

**Refuses to execute if no tradeoffs have been declared** — the server enforces that every Critique must be resolved first. Uses Sampling to delegate synthesis to the client LLM, passing both the original architecture text and all declared tradeoff statements.

**Input**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `architecture_id` | string | ✅ | UUID of the architecture to finalize |

**Output**
```json
{
  "status": "finalized",
  "final_architecture": "..."
}
```

---

### `list_roots_scope` *(sync)*

Returns a list of root constraint IDs loaded from `data/roots.json`. Used by connected clients to discover what constraints are active without reading the file directly.

---

### `list_futures_scope` *(sync)*

Returns a list of future IDs loaded from `data/futures.json`. Used by the LangGraph host at graph build time to discover futures dynamically — no hardcoding required.

---

### `write_architecture` *(sync)*

Writes an architecture document to `architectures/<use_case>/` on disk.

**Input**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `use_case` | string | ✅ | Folder name for this design session |
| `doc_type` | string | ✅ | One of: `initial`, `simulated_future`, `final` |
| `content` | string | ✅ | Full document text to write |
| `future_name` | string | — | Required when `doc_type` is `simulated_future` |

---

## Resources

Two MCP Resources are exposed for any client to read directly:

| URI | Contents |
|---|---|
| `roots://governance` | Full contents of `data/roots.json` |
| `roots://futures` | Full contents of `data/futures.json` |

---

## State Management

All runtime state is held in two in-memory dicts. Both reset on server restart — for persistent multi-session deployments, replace them with a database.

| Store | File | Contents |
|---|---|---|
| `REVIEW_STORE` | `store.py` | One entry per architecture: initial text, tradeoff list, critique ID list, final text |
| `CRITIQUE_STORE` | `critiques.py` | One entry per `Critique` object, keyed by UUID |

### REVIEW_STORE schema

```python
REVIEW_STORE[architecture_id] = {
    "initial_architecture": str,   # raw text from generate_architecture_tool
    "tradeoffs": [                 # appended by declare_tradeoff()
        {"critique_id": str, "statement": str}
    ],
    "critiques": [str],            # list of critique UUIDs
    "final_architecture": str | None
}
```

---

## MCP Features

| Feature | Used In |
|---|---|
| **Tools** | All eight `@mcp.tool()` functions |
| **Resources** | `roots://governance`, `roots://futures` |
| **Sampling** (`ctx.session.create_message`) | `generate_architecture_tool`, `simulate_future_tool`, `propose_tradeoff_tool` (phase 1), `finalize_architecture_tool` — the server delegates all LLM calls back to the client |
| **Elicitation** (`ctx.elicit`) | `propose_tradeoff_tool` (phase 2) — the server presents tradeoff options and waits for a human selection |

---

## Installation

```bash
# From the project root
python -m venv .venv

# Windows
.venv\Scripts\activate
# Unix / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Running

### stdio (default — for programmatic clients and the LangGraph host)

```bash
python -m server.mcp_server
```

### Streamable HTTP

Change the last line of `mcp_server.py`:

```python
mcp.run(transport="streamable-http")
# Server available at http://127.0.0.1:8000/mcp
```

---

## Customising Roots and Futures

Both files are plain JSON. No code changes are required — the server reloads them on next startup.

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

### Adding a Future (`data/futures.json`)

The `review_prompt` must instruct the model to respond only in JSON with `summary` (string) and `risks` (array of strings). Markdown fences are stripped automatically if the model includes them.

```json
{
  "your_future_id": {
    "id": "your_future_id",
    "description": "What this scenario assumes.",
    "assumption": "The specific pessimistic assumption.",
    "stance": "pessimistic | adversarial | literal",
    "stress_points": ["..."],
    "failure_modes": ["..."],
    "early_warning_signals": ["..."],
    "review_prompt": "You are a [role]. Given this architecture... Respond ONLY in JSON: {\"summary\": \"...\", \"risks\": [\"...\"]}"
  }
}
```

---

## Claude Desktop

> ⚠️ **Not compatible with this branch.**
>
> This server uses MCP Sampling and MCP Elicitation, which Claude Desktop does not currently support. Connecting it directly will result in tool calls that silently fail or hang.
>
> Switch to the `simple-server` branch for a Claude Desktop-compatible version:
>
> ```bash
> git checkout simple-server
> ```

---

## Design Principles

**Authority belongs to the server.** Governance prompts — root constraints, future scenarios, critique structure — all live here. The client cannot skip or alter them.

**The server can say no.** `finalize_architecture_tool` refuses to produce output until every Critique is resolved by a declared Tradeoff.

**Tradeoffs are first-class artifacts.** Every accepted tradeoff is persisted and passed verbatim into the finalization prompt. Nothing is silently discarded.

**The server never chooses the tradeoff.** That decision always belongs to the human, enforced via MCP Elicitation.