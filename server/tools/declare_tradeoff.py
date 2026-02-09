from server.resources.critiques import get_critique

def declare_tradeoff(critique_id: str, tradeoff_statement: str) -> dict:
    critique = get_critique(critique_id)

    if not critique:
        return {"status": "error", "reason": "Critique not found"}

    if len(tradeoff_statement.strip()) < 30:
        return {
            "status": "rejected",
            "reason": "Tradeoff declaration too weak."
        }

    critique.required_tradeoff = tradeoff_statement
    critique.resolved = True

    return {
        "status": "accepted",
        "message": "Tradeoff recorded and critique resolved",
        "critique_id": critique_id,
        "tradeoff_statement": tradeoff_statement
    }
