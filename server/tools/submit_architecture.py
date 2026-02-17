from server.resources.architectures import create_architecture
from server.resources.roots import load_roots
from server.state.store import REVIEW_STORE

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
    REVIEW_STORE[architecture.id] = {
        "initial_architecture": description,
        "tradeoffs": [],
        "critiques": [],
        "final_architecture": None
    }

    return {
        "status": "saved",
        "architecture_id": architecture.id
    }
