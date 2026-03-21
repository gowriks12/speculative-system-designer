"""
Roots loader and prompt formatter.

Roots are non-negotiable architectural constraints defined in data/roots.json.
They are injected into the architecture generation prompt so the client LLM
cannot produce a design that ignores them.

Each root has:
  - id, statement, rationale, violation_examples
"""

import json
from pathlib import Path

SERVER_PATH = Path(__file__).parent

_DATA_PATH = SERVER_PATH / "data" / "roots.json"


def load_roots() -> dict:
    """
    Load and return the root constraints from data/roots.json.

    Returns:
        Dict keyed by root ID (e.g. "team_constraints", "reversibility").

    Raises:
        FileNotFoundError: If data/roots.json does not exist.
    """
    with open(_DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def format_roots_for_prompt(roots: dict) -> str:
    """
    Format the roots dict into a structured string suitable for LLM prompts.

    Each root is rendered with its requirement, rationale, and examples of
    what to avoid. This block is injected verbatim into the architecture
    generation prompt.

    Args:
        roots: Dict returned by load_roots().

    Returns:
        Multi-line string listing all roots in a readable format.
    """
    lines = []
    for root in roots.values():
        avoid = "\n    - ".join(root["violation_examples"])
        lines.append(
            f"ROOT: {root['id']}\n"
            f"  Requirement : {root['statement']}\n"
            f"  Rationale   : {root['rationale']}\n"
            f"  Avoid       :\n"
            f"    - {avoid}"
        )
    return "\n\n".join(lines)
