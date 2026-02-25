import json
from pathlib import Path
from datetime import datetime
from mcp.server.fastmcp import FastMCP

from server.resources.roots import *
from server.resources.futures import *
from server.prompts.templates import *
mcp = FastMCP("speculative-system-designer")

# ── Storage ────────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data"

OUTPUT_DIR = Path(__file__).parent.parent / "architectures"  # pre-defined output location
OUTPUT_DIR.mkdir(exist_ok=True)

FUTURES_FILE = DATA_DIR / "futures.json"
ROOTS_FILE   = DATA_DIR / "roots.json"

FUTURES = load_futures()
ROOTS = load_roots()

def _save(path, data):
    path.write_text(json.dumps(data, indent=2))


# ── Resources ──────────────────────────────────────────────────────────────────

@mcp.resource("design://futures")
def get_futures() -> str:
    """All registered speculative future scenarios."""
    return load_futures()


@mcp.resource("design://roots")
def get_roots() -> str:
    """All registered root constraints the architecture must satisfy."""
    return load_roots()


# ── Prompts ────────────────────────────────────────────────────────────────────

@mcp.prompt()
def generate_initial_architecture(system_description: str) -> str:
    """Generate an initial architecture that satisfies all root constraints."""
    return initial_architecture_prompt(system_description)

@mcp.prompt()
def simulate_future(future_name: str, architecture: str) -> str:
    """Stress-test an architecture against a specific registered future scenario."""
    return simulating_future(future_name, architecture)

@mcp.prompt()
def identify_tradeoffs(architecture: str, simulation_results: str) -> str:
    """Analyse simulation results to surface tradeoffs and failure modes."""
    return pickup_issues(architecture, simulation_results)

@mcp.prompt()
def generate_final_architecture(system_description: str, initial_architecture: str, tradeoffs_and_issues: str) -> str:
    """Generate the final resilient architecture incorporating all simulation learnings."""
    return final_architecture_prompt(system_description,initial_architecture, tradeoffs_and_issues)


# ── Tools ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_roots_scope():
    """List the future scopes available to simulate"""
    return list(ROOTS.keys())

@mcp.tool()
def list_futures_scope():
    """List the future scopes available to simulate"""
    return list(FUTURES.keys())


@mcp.tool()
def write_architecture(use_case: str, doc_type: str, content: str, future_name: str = "") -> str:
    """Write an architecture document to the architectures/<use_case>/ folder.

    doc_type must be one of: 'initial', 'simulated_future', 'final'.
    For 'simulated_future', also provide future_name.
    """
    safe = lambda s: "".join(c if c.isalnum() or c in " -_" else "_" for c in s).strip()

    folder = OUTPUT_DIR / safe(use_case)
    folder.mkdir(parents=True, exist_ok=True)

    match doc_type:
        case "initial":
            filename = "Initial Architecture.txt"
        case "simulated_future":
            filename = f"Simulated Future - {safe(future_name)}.txt"
        case "final":
            filename = "Final Architecture.txt"
        case _:
            return f"Unknown doc_type '{doc_type}'. Use: initial, simulated_future, or final."

    header = f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n{'='*60}\n\n"
    (folder / filename).write_text(header + content, encoding="utf-8")
    return f"Saved to: {folder / filename}"


# ── Run ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
