import json
from pathlib import Path
from datetime import datetime
from fastmcp import FastMCP

from resources.roots import *
from resources.futures import *
from prompts.templates import *
mcp = FastMCP("speculative-system-designer")

# ── Storage ────────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data"


OUTPUT_DIR = Path(__file__).parent.parent / "architectures"  # pre-defined output location
OUTPUT_DIR.mkdir(exist_ok=True)

FUTURES_FILE = DATA_DIR / "futures.json"
ROOTS_FILE   = DATA_DIR / "roots.json"

FUTURES = load_futures()

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
    return load_roots


# ── Prompts ────────────────────────────────────────────────────────────────────

@mcp.prompt()
def generate_initial_architecture(system_description: str) -> str:
    """Generate an initial architecture that satisfies all root constraints."""
    return generate_initial_architecture(system_description)


@mcp.prompt()
def simulate_future(future_name: str, architecture: str) -> str:
    """Stress-test an architecture against a specific registered future scenario."""
    return simulate_future(future_name, architecture)

@mcp.prompt()
def identify_tradeoffs(architecture: str, simulation_results: str) -> str:
    """Analyse simulation results to surface tradeoffs and failure modes."""
    return f"""You are a senior systems architect doing cross-future analysis.

## Original Architecture
{architecture}

## Simulation Results
{simulation_results}

## Root Constraints
{json.dumps(roots, indent=2)}

Produce a Markdown report titled "Tradeoffs & Issues" covering: Recurring Failures, Architectural Tensions, Constraint Fragility, Opportunity Areas, and Top Priority Issues to fix."""


@mcp.prompt()
def generate_final_architecture(system_description: str, initial_architecture: str, tradeoffs_and_issues: str) -> str:
    """Generate the final resilient architecture incorporating all simulation learnings."""
    return f"""You are a senior systems architect producing a final battle-tested design.

## System
{system_description}

## Initial Architecture
{initial_architecture}

## Tradeoffs & Issues to Address
{tradeoffs_and_issues}

## Root Constraints
{json.dumps(roots, indent=2)}

## Futures to be Resilient Against
{json.dumps(futures, indent=2)}

Produce a comprehensive Markdown document titled "Final Architecture" with: what changed and why, updated Components, Resilience Mechanisms per future, and Remaining Risks."""


# ── Tools ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def add_future(name: str, description: str, drivers: list[str] = [], implications: list[str] = []) -> str:
    """Register a speculative future scenario."""
    global futures
    if any(f["name"] == name for f in futures):
        return f"Future '{name}' already exists. Remove it first to update."
    futures.append({"name": name, "description": description, "drivers": drivers, "implications": implications})
    _save(FUTURES_FILE, futures)
    return f"Registered future: {name}"


@mcp.tool()
def add_root(name: str, description: str, category: str = "other", rationale: str = "") -> str:
    """Register a root constraint the architecture must satisfy."""
    global roots
    if any(r["name"] == name for r in roots):
        return f"Root '{name}' already exists. Remove it first to update."
    roots.append({"name": name, "description": description, "category": category, "rationale": rationale})
    _save(ROOTS_FILE, roots)
    return f"Registered root constraint: {name}"


@mcp.tool()
def remove_future(name: str) -> str:
    """Remove a future scenario by name."""
    global futures
    futures = [f for f in futures if f["name"] != name]
    _save(FUTURES_FILE, futures)
    return f"Removed future: {name}"


@mcp.tool()
def remove_root(name: str) -> str:
    """Remove a root constraint by name."""
    global roots
    roots = [r for r in roots if r["name"] != name]
    _save(ROOTS_FILE, roots)
    return f"Removed root: {name}"


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
