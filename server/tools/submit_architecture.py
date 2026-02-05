from server.resources.architectures import create_architecture
from server.resources.roots import load_roots

def evaluate_roots(architecture_text: str) -> list[str]:
    """
    Very naive implementation to start.
    This will improve later.
    """
    roots = load_roots()
    violations = []

    for root_id, root in roots.items():
        # placeholder logic — intentionally simple
        if root_id == "team_constraints":
            if "manual" in architecture_text.lower():
                violations.append(root["statement"])

        if root_id == "reversibility":
            if "hard-coded" in architecture_text.lower():
                violations.append(root["statement"])

    return violations


def submit_architecture(description: str) -> dict:
    architecture = create_architecture(description)
    violations = evaluate_roots(description)

    if violations:
        architecture.status = "rejected"
        architecture.root_violations = violations

        return {
            "status": "rejected",
            "reason": "Root constraints violated",
            "violations": violations
        }

    architecture.status = "under_review"

    return {
        "status": "accepted",
        "architecture_id": architecture.id,
        "message": "Architecture accepted for future review"
    }
