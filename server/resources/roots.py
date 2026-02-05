import json
from pathlib import Path

ROOTS_PATH = Path("data/roots.json")

def load_roots() -> dict:
    with open(ROOTS_PATH, "r") as f:
        return json.load(f)
