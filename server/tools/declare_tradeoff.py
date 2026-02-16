from server.resources.critiques import get_critique

from server.state.store import REVIEW_STORE
from server.resources.critiques import CRITIQUE_STORE

def declare_tradeoff(architecture_id: str,
                     critique_id: str,
                     tradeoff_statement: str) -> dict:

    if architecture_id not in REVIEW_STORE:
        return {"status": "error", "reason": "Unknown architecture"}

    critique = CRITIQUE_STORE.get(critique_id)
    if not critique:
        return {"status": "error", "reason": "Unknown critique"}

    # Store tradeoff
    REVIEW_STORE[architecture_id]["tradeoffs"].append({
        "critique_id": critique_id,
        "statement": tradeoff_statement
    })

    critique.required_tradeoff = tradeoff_statement
    critique.resolved = True

    return {
        "status": "accepted",
        "message": "Tradeoff stored",
        "total_tradeoffs": len(REVIEW_STORE[architecture_id]["tradeoffs"])
    }

