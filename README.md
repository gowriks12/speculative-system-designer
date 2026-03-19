# LangGraph Host for Speculative System Designer

Drop the `host/` folder into the root of your existing
`SpeculativeSystemDesigner` project. The directory layout should look like:

```
SpeculativeSystemDesigner/
├── data/
│   ├── futures.json
│   └── roots.json
├── server/
│   ├── mcp_server.py          ← add list_futures_tool (see step 1 below)
│   ├── resources/
│   ├── state/
│   └── tools/
├── host/                      ← new folder from this package
│   ├── __init__.py
│   ├── state.py
│   ├── handlers.py
│   ├── nodes.py
│   ├── graph.py
│   └── run.py
├── graph_flow.svg             ← graph flow diagram (reference)
├── list_futures_tool_snippet.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## 1. Add `list_futures_tool` to the server

Open `server/mcp_server.py` and paste the contents of
`list_futures_tool_snippet.py` after the existing `@mcp.tool()` definitions:

```python
@mcp.tool()
def list_futures_tool() -> str:
    """Return all available future scenario IDs and their metadata."""
    futures = load_futures()
    return json.dumps({
        fid: {
            "description": f["description"],
            "stance":       f["stance"],
            "assumption":   f["assumption"],
        }
        for fid, f in futures.items()
    }, indent=2)
```

---

## 2. Install dependencies

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# Unix / Mac
source .venv/bin/activate

pip install -r requirements.txt
```

---

## 3. Configure environment

```bash
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY
```

If your venv Python is not at the default path, set `SERVER_PYTHON` in `.env`.

---

## 4. Run

```bash
# Full run: generate, draw initial, simulate futures, finalize, draw final
python -m host.run

# Skip evaluation: generate + draw initial only, then END
python -m host.run --no-eval
```

---

## Graph flow

```
generate
  └─► draw_initial (Excalidraw)
          ├─[--no-eval]──────────────────────────────► END
          └─[default]──► simulate_future ◄─────────────┐
                              └─► propose_tradeoff       │
                                      ├─[more futures]──┘
                                      └─[done]──► finalize
                                                     └─► draw_final (Excalidraw)
                                                               └─► END
```

See `graph_flow.svg` for a visual version.

---

## Elicitation modes

| Mode | Behaviour | Set via |
|------|-----------|---------|
| `llm` (default) | LLM auto-selects A/B/C | `ELICITATION_MODE=llm` |
| `human` | Graph pauses via `interrupt()` | `ELICITATION_MODE=human` |

### Resuming a paused graph (human mode)

```python
from langgraph.types import Command

# First call pauses at the first elicitation
result = await graph.ainvoke(initial_state, config=config)

# Resume with the human's selection
result = await graph.ainvoke(Command(resume="B"), config=config)
```

---

## Excalidraw integration

The host connects to the Excalidraw MCP server at `https://mcp.excalidraw.com/mcp`
(override with `EXCALIDRAW_MCP_URL` in `.env`).

Two diagrams are produced per run:
- **Initial diagram** — rendered right after architecture generation
- **Final diagram** — rendered after all tradeoffs are resolved

Both URLs are stored in `DesignState` and printed at the end of the run.

---

## Swapping the LLM

The host uses OpenAI by default. To switch to Anthropic, edit `host/handlers.py`
and `host/nodes.py`:

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
