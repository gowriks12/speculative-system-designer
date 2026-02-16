import json
from pathlib import Path

ROOTS_PATH = Path("data/roots.json")

def load_roots() -> dict:
    with open(ROOTS_PATH, "r") as f:
        return json.load(f)

def format_roots_for_prompt(roots):
    formatted = ""
    for root in roots.values():
        formatted += f"""
    ROOT: {root['id']}
    Requirement: {root['statement']}
    Rationale: {root['rationale']}
    Avoid:
    - {chr(10).join(root['violation_examples'])}
    """
    return formatted