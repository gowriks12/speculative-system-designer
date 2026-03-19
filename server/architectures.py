"""
Architecture model and factory.

An Architecture represents a proposed system design submitted for review.
It is created by submit_architecture() and stored in REVIEW_STORE alongside
its critiques and tradeoffs.
"""

from uuid import uuid4
from pydantic import BaseModel
from store import REVIEW_STORE


class Architecture(BaseModel):
    """A proposed system architecture submitted for governance review."""

    id: str
    """Unique identifier (UUID4) assigned at creation time."""

    description: str
    """Full text of the architecture proposal."""

    status: str
    """Lifecycle status: 'submitted' | 'under_review' | 'approved' | 'rejected'."""

    root_violations: list[str] = []
    """Root constraints violated by this architecture (populated during review)."""


def create_architecture(description: str) -> Architecture:
    """
    Create a new Architecture with status 'submitted'.

    Args:
        description: Plain-text architecture proposal.

    Returns:
        A freshly created Architecture instance with a new UUID.
    """
    return Architecture(
        id=str(uuid4()),
        description=description,
        status="submitted",
        root_violations=[],
    )

"""
submit_architecture — save an architecture for review.

This module is the single point of entry for persisting a new architecture.
It creates the Architecture model, sets up its review record in REVIEW_STORE,
and returns the generated ID to the caller.
"""

def submit_architecture(description: str) -> dict:
    """
    Save an architecture description and initialise its review record.

    Creates a new Architecture object (with a fresh UUID), then inserts an
    entry into REVIEW_STORE so that simulate_future_tool, propose_tradeoff_tool,
    and finalize_architecture_tool can find it by ID.

    Args:
        description: Full text of the architecture proposal.

    Returns:
        {
            "status": "saved",
            "architecture_id": "<uuid>"
        }
    """
    architecture = create_architecture(description)

    REVIEW_STORE[architecture.id] = {
        "initial_architecture": description,
        "tradeoffs": [],       # list of {"critique_id": str, "statement": str}
        "critiques": [],       # list of critique UUIDs
        "final_architecture": None,
    }

    return {
        "status": "saved",
        "architecture_id": architecture.id,
    }

