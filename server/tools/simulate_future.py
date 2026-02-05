from server.resources.critiques import create_scaling_critique

def simulate_scaling_future(architecture_text: str) -> dict:
    """
    Simulates the scaling future and produces a critique artifact.
    """
    risks = []

    text = architecture_text.lower()

    if "single" in text:
        risks.append("Single point of failure under scale.")

    if "synchronous" in text:
        risks.append("Synchronous processing limits throughput.")

    if "manual" in text:
        risks.append("Manual operations will not scale with load.")

    if not risks:
        risks.append("Scaling risks unclear due to vague architecture.")

    critique = create_scaling_critique(risks)

    return {
        "status": "critique_generated",
        "critique": critique.model_dump()
    }
