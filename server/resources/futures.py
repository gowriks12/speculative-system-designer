from pathlib import Path
import json

ROOT_PATH = Path(__file__).parent.parent.parent
def load_futures():
    with open(ROOT_PATH / "data/futures.json", "r") as f:
        FUTURES = json.load(f)
        return FUTURES