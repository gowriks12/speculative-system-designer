# Speculative System Designer

> An MCP server that acts as its own best critic — generating, stress-testing, and governing software architectures through structured futures and explicit tradeoffs.

---

## What Is This?

Most architecture tools help you build. This one helps you **question**.

Speculative System Designer is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that:

1. **Generates** a system architecture constrained by non-negotiable *root principles* (team size, cost, observability, reversibility).
2. **Stress-tests** it across pessimistic *futures* — scaling pressure, security abuse, regulatory change.
3. **Surfaces critiques** for each failure scenario and asks you to choose a tradeoff.
4. **Finalizes** a revised architecture that honestly reflects every accepted tradeoff.

The key insight is that **authority belongs to the server, creativity belongs to the client**. Prompts that encode judgment (root constraints, future scenarios, critique structure) live inside the MCP server. The client LLM handles synthesis.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        MCP Client                           │
│          (Claude Desktop / custom client)                   │
└────────────────────────┬────────────────────────────────────┘
                         │  MCP (stdio / streamable-http)
┌────────────────────────▼────────────────────────────────────┐
│                   MCP Server (FastMCP)                      │
│                                                             │
│  Tools                          Resources                   │
│  ├─ generate_architecture_tool  ├─ roots://governance       │
│  ├─ evaluate_architecture_tool  └─ roots://futures          │
│  ├─ simulate_future_tool                                    │
│  ├─ propose_tradeoff_tool       State                       │
│  ├─ finalize_architecture_tool  └─ REVIEW_STORE (in-memory) │
│  └─ submit_architecture_tool                                │
│                                                             │
│  Data                                                       │
│  ├─ data/roots.json    ← non-negotiable constraints         │
│  └─ data/futures.json  ← pessimistic stress scenarios       │
└─────────────────────────────────────────────────────────────┘
```

### Key Concepts

| Concept | Description |
|---|---|
| **Root** | A non-negotiable architectural constraint (e.g. "must be operable by ≤ 6 engineers"). Violations block approval. |
| **Future** | A pessimistic scenario used to stress-test the architecture (scaling 10x, security abuse, regulatory change). |
| **Critique** | Structured feedback produced by simulating a future against an architecture — includes a summary and specific risks. |
| **Tradeoff** | An explicit, human-accepted compromise that resolves a critique. Must be declared before the architecture is finalized. |

---

## Project Structure

```
speculative-system-designer/
├── server/
│   ├── mcp_server.py           # FastMCP entry point — all tools registered here
│   ├── resources/
│   │   ├── architectures.py    # Architecture model + factory
│   │   ├── critiques.py        # Critique model, store, and helpers
│   │   ├── futures.py          # Loads futures.json
│   │   └── roots.py            # Loads roots.json + prompt formatting
│   ├── tools/
│   │   ├── submit_architecture.py   # Saves architecture to REVIEW_STORE
│   │   └── declare_tradeoff.py      # Records an accepted tradeoff
│   └── state/
│       └── store.py            # In-memory REVIEW_STORE dict
│
├── data/
│   ├── roots.json              # Constitutional constraints
│   └── futures.json            # Stress-test scenarios + review prompts
│
├── docs/
│   ├── TOOLS.md                # Tool-by-tool API reference
│   └── CONCEPTS.md             # Deep dive into roots, futures, and tradeoffs
│
├── pyproject.toml
└── README.md
```

---

## Quickstart

### Prerequisites

- Python 3.11+
- [Claude Desktop](https://claude.ai/download) (or any MCP-compatible client)

### Installation

```bash
git clone https://github.com/yourname/speculative-system-designer
cd speculative-system-designer

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e .
```

### Run with Claude Desktop

Add the following to your `claude_desktop_config.json` (usually at `~/Library/Application Support/Claude/` on macOS or `%APPDATA%\Claude\` on Windows):

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

Restart Claude Desktop. You should see the server connect in the toolbar.

### Run as HTTP Server

```bash
# In mcp_server.py, change the last line to:
mcp.run(transport="streamable-http")

# Then start:
python -m server.mcp_server
# Server available at http://127.0.0.1:8000/mcp
```

---

## Workflow

A full design session proceeds in four stages:

```
1. generate_architecture_tool(problem_statement)
        │
        ▼  (LLM proposes architecture obeying roots via MCP Sampling)
        
2. evaluate_architecture_tool(architecture_id)
        │
        ├─ simulate_future_tool × 3 futures  (scaling, security, compliance)
        │       │
        │       ▼  (LLM critiques each future via MCP Sampling)
        │
        └─ propose_tradeoff_tool × 3 critiques
                │
                ▼  (Server presents 3 options → User picks via MCP Elicitation)
                
3. finalize_architecture_tool(architecture_id)
        │
        ▼  (LLM rewrites architecture incorporating accepted tradeoffs)
        
4. ✅  Final governed architecture
```

### Example Prompt (Claude Desktop)

```
Design a backend system that ingests events asynchronously, processes them in 
near-real-time, and exposes analytics APIs for customers. The team has 4 engineers.
```

Claude will call `generate_architecture_tool`, then `evaluate_architecture_tool`, presenting you with tradeoff choices along the way before producing a finalized, self-aware architecture.

---

## Configuring Roots and Futures

### Roots (`data/roots.json`)

Each root is a hard constraint the generated architecture must satisfy. Edit or add roots freely:

```json
{
  "your_root_id": {
    "id": "your_root_id",
    "statement": "The constraint in plain language.",
    "rationale": "Why this constraint exists.",
    "violation_examples": [
      "example of something that would break this constraint"
    ]
  }
}
```

### Futures (`data/futures.json`)

Each future is a pessimistic scenario. The `review_prompt` is sent verbatim to the LLM (via MCP Sampling) along with the architecture text. It **must** instruct the model to respond in JSON with `summary` (string) and `risks` (array of strings):

```json
{
  "your_future_id": {
    "id": "your_future_id",
    "description": "What this future assumes.",
    "review_prompt": "You are a [role]. Given this architecture... Respond ONLY in JSON: {\"summary\": \"...\", \"risks\": [\"...\"]}"
  }
}
```

---

## MCP Features Used

| Feature | Where Used |
|---|---|
| **Tools** | All six `@mcp.tool()` functions — the primary interaction surface |
| **Resources** | `roots://governance` and `roots://futures` — readable by clients |
| **Sampling** | Architecture generation, future simulation, tradeoff proposal, finalization — the server delegates LLM calls back to the client |
| **Elicitation** | `propose_tradeoff_tool` — server asks the human to choose a tradeoff option |

---

## Design Principles

**Authority belongs to the server.** The prompts encoding judgment — root constraints, future scenarios, critique structure — all live inside the MCP server. The client cannot bypass them.

**Creativity belongs to the client.** The client LLM handles open-ended synthesis: proposing architectures, generating options, writing the final document.

**Tradeoffs are first-class artifacts.** Every accepted tradeoff is persisted in `REVIEW_STORE` and incorporated into the final architecture. Nothing is silently discarded.

**The server can say no.** If tradeoffs haven't been declared, `finalize_architecture_tool` refuses to produce a final architecture.

---

## Development

```bash
# Run tests (if added)
pytest

# Type checking
mypy server/

# Linting
ruff check server/
```

---

## License

MIT
