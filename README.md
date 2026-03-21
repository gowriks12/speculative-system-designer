# Speculative System Designer

> An MCP server that acts as its own best critic — generating, stress-testing, and governing software architectures through structured futures and explicit tradeoffs.

---

## What Is This?

Most architecture tools help you build. This one helps you **question**.

Speculative System Designer is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that guides Claude through a four-stage design process:

1. **Generate** an initial architecture constrained by non-negotiable root principles.
2. **Simulate** pessimistic futures against it — scaling pressure, security abuse, regulatory change.
3. **Identify** tradeoffs and failure modes across all simulations.
4. **Finalize** a revised architecture that honestly reflects every accepted tradeoff.

The key insight: **prompts that encode judgment belong to the server, synthesis belongs to the client.** Root constraints and future scenarios live inside the MCP server — Claude cannot bypass them.

---

## How It Works

This branch exposes the design workflow as **MCP Prompts**. Rather than the server autonomously calling the LLM, Claude receives a structured prompt at each stage and produces the output itself. You step Claude through the process in order.

```
1. generate_initial_architecture(system_description)
        ↓
   Claude produces an architecture obeying all root constraints

2. simulate_future(future_name, architecture)      ← run once per future
        ↓
   Claude stress-tests the architecture against a pessimistic scenario

3. identify_tradeoffs(architecture, simulation_results)
        ↓
   Claude surfaces recurring failures, tensions, and priority fixes

4. generate_final_architecture(system_description, initial_architecture, tradeoffs_and_issues)
        ↓
   Claude produces a final battle-tested design
```

---

## Project Structure

```
speculative-system-designer/
├── server/
│   ├── mcp_server.py           # FastMCP entry point — prompts, tools, resources
│   ├── resources/
│   │   ├── roots.py            # Loads roots.json + formats for prompts
│   │   └── futures.py          # Loads futures.json
│   └── prompts/
│       └── templates.py        # Prompt template functions
│
├── data/
│   ├── roots.json              # Non-negotiable architectural constraints
│   └── futures.json            # Pessimistic stress-test scenarios
│
├── architectures/              # Generated output documents (created at runtime)
├── requirements.txt
└── README.md
```

---

## Prompts

### `generate_initial_architecture`
Produces an initial architecture that explicitly satisfies every root constraint.

| Parameter | Description |
|---|---|
| `system_description` | Plain-language description of the system to design |

---

### `simulate_future`
Stress-tests an architecture against one future scenario, identifying what holds, degrades, and breaks.

| Parameter | Description |
|---|---|
| `future_name` | ID of a future from `data/futures.json` (e.g. `scaling`, `security_abuse`, `regulatory_compliance`) |
| `architecture` | The architecture text to test (output from the previous step) |

Run this once per future. Use `list_futures_scope` to see all available futures.

---

### `identify_tradeoffs`
Cross-analyses all simulation results to surface recurring failures, architectural tensions, constraint fragility, and top priority issues.

| Parameter | Description |
|---|---|
| `architecture` | The initial architecture text |
| `simulation_results` | Combined output from all `simulate_future` runs |

---

### `generate_final_architecture`
Produces a final, battle-tested architecture that addresses all identified tradeoffs and issues.

| Parameter | Description |
|---|---|
| `system_description` | Original system description |
| `initial_architecture` | Output from `generate_initial_architecture` |
| `tradeoffs_and_issues` | Output from `identify_tradeoffs` |

---

## Tools

### `list_roots_scope`
Returns the list of root constraint IDs currently loaded from `data/roots.json`.

### `list_futures_scope`
Returns the list of future scenario IDs currently loaded from `data/futures.json`.

### `write_architecture`
Saves an architecture document to `architectures/<use_case>/`.

| Parameter | Type | Description |
|---|---|---|
| `use_case` | string | Folder name for the project (e.g. `"concert_ticketing_platform"`) |
| `doc_type` | string | One of: `initial`, `simulated_future`, `final` |
| `content` | string | The document content to save |
| `future_name` | string | Required when `doc_type` is `simulated_future` |

---

## Resources

Two MCP Resources are exposed for clients to read directly:

| URI | Contents |
|---|---|
| `design://roots` | Full `data/roots.json` — the root constraints |
| `design://futures` | Full `data/futures.json` — the future scenarios |

---

## Configuring Roots and Futures

### Roots (`data/roots.json`)

Roots are non-negotiable constraints injected into every architecture generation prompt. The four defaults are:

| Root | Statement |
|---|---|
| `team_constraints` | Must be buildable and operable by 6 engineers or fewer |
| `cost_discipline` | Infrastructure costs must be predictable and defensible |
| `operational_observability` | Must be diagnosable without ad-hoc production instrumentation |
| `reversibility` | Major decisions must be reversible without a full rewrite |

Add or edit roots freely — changes take effect on the next prompt call with no code changes needed:

```json
{
  "your_root_id": {
    "id": "your_root_id",
    "statement": "The constraint in plain language.",
    "rationale": "Why this constraint exists.",
    "violation_examples": ["example of something that breaks this rule"]
  }
}
```

### Futures (`data/futures.json`)

Futures are pessimistic scenarios used to stress-test architectures. The three defaults are `scaling`, `security_abuse`, and `regulatory_compliance`. Add your own:

```json
{
  "your_future_id": {
    "id": "your_future_id",
    "description": "What this scenario assumes.",
    "review_prompt": "Instructions for Claude on how to evaluate the architecture under this scenario."
  }
}
```

---

## Setup

### Prerequisites

- Python 3.11+
- Claude Desktop (or any MCP-compatible client)

### Install

```bash
git clone https://github.com/yourname/speculative-system-designer
cd speculative-system-designer

python -m venv .venv

# macOS / Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

### Claude Desktop Integration

Add to your `claude_desktop_config.json`:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

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

On Windows:

```json
{
  "mcpServers": {
    "speculative-system-designer": {
      "command": "C:\\path\\to\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\server\\mcp_server.py"],
      "cwd": "C:\\path\\to\\speculative-system-designer",
      "env": {
        "PYTHONPATH": "C:\\path\\to\\speculative-system-designer"
      }
    }
  }
}
```

Restart Claude Desktop. The server will appear as a connected tool source.

---

## Example Session

```
You: Use the generate_initial_architecture prompt to design a backend that 
     ingests IoT sensor events and exposes analytics dashboards to 10,000 customers.

Claude: [produces architecture obeying all roots]

You: Now simulate the scaling future against this architecture.

Claude: [produces scaling critique]

You: Simulate security_abuse too.

Claude: [produces security critique]

You: Now identify the tradeoffs across both simulations.

Claude: [surfaces recurring failures and tensions]

You: Generate the final architecture and save it.

Claude: [produces final architecture, calls write_architecture to persist it]
```

---

## Design Principles

**Authority belongs to the server.** Root constraints and future scenarios are baked into server-side prompts. Claude cannot produce an architecture that ignores them.

**Creativity belongs to the client.** Claude handles all open-ended synthesis — proposing architectures, critiquing futures, writing the final document.

**Futures are not risks.** A future is a world the system might have to operate in. The question is not whether it will happen — it is what breaks first when it does.