"""
declare_tradeoff — record an accepted tradeoff against a critique.

Called by propose_tradeoff_tool after the user selects one of the generated
options. Persists the chosen statement in REVIEW_STORE and marks the
associated Critique as resolved so unresolved_critiques() stays accurate.
"""

from critiques import CRITIQUE_STORE
from store import REVIEW_STORE


def declare_tradeoff(
    architecture_id: str,
    critique_id: str,
    tradeoff_statement: str,
) -> dict:
    """
    Record an accepted tradeoff and mark the critique as resolved.

    Args:
        architecture_id: UUID of the architecture under review.
        critique_id: UUID of the Critique being resolved.
        tradeoff_statement: Plain-language description of the accepted tradeoff.

    Returns:
        On success:
            {
                "status": "accepted",
                "message": "Tradeoff stored",
                "total_tradeoffs": <int>
            }
        On failure:
            {"status": "error", "reason": "<description>"}
    """
    if architecture_id not in REVIEW_STORE:
        return {"status": "error", "reason": f"Unknown architecture_id: {architecture_id}"}

    critique = CRITIQUE_STORE.get(critique_id)
    if not critique:
        return {"status": "error", "reason": f"Unknown critique_id: {critique_id}"}

    REVIEW_STORE[architecture_id]["tradeoffs"].append({
        "critique_id": critique_id,
        "statement": tradeoff_statement,
    })

    critique.required_tradeoff = tradeoff_statement
    critique.resolved = True

    return {
        "status": "accepted",
        "message": "Tradeoff stored",
        "total_tradeoffs": len(REVIEW_STORE[architecture_id]["tradeoffs"]),
    }
