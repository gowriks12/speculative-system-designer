def declare_tradeoff(critique_id: str, tradeoff_statement: str) -> dict:
    if not tradeoff_statement or len(tradeoff_statement.strip()) < 20:
        return {
            "status": "rejected",
            "reason": "Tradeoff declaration too weak or missing."
        }

    return {
        "status": "accepted",
        "message": "Tradeoff recorded. Critique can be resolved.",
        "tradeoff": tradeoff_statement
    }


