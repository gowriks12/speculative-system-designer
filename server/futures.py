"""
Futures loader.

Futures are pessimistic scenarios used to stress-test architectures.
They are defined in data/futures.json and loaded once at server startup.

Each future has:
  - id, description, assumption, stance
  - stress_points, failure_modes, early_warning_signals
  - review_prompt  ← sent verbatim to the LLM via MCP Sampling
"""

import json
from pathlib import Path

_DATA_PATH = Path(__file__) / "data" / "futures.json"


def load_futures() -> dict:
    """
    Load and return the futures catalogue from data/futures.json.

    Returns:
        Dict keyed by future ID (e.g. "scaling", "security_abuse").

    Raises:
        FileNotFoundError: If data/futures.json does not exist.
    """
    with open(_DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def future_prompt(future) -> str:
    """
    Return the future simulation prompt for the future from the future dictionary
    
    Returns:
        String which is the prompt to carry out future simulation
    """
    return future["review_prompt"]
