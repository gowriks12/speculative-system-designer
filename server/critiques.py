"""
Critique model, in-memory store, and helper functions.

A Critique is produced by simulating a Future against an architecture.
It captures what would go wrong, why, and what observable signals would appear.
Critiques are resolved by declaring an explicit Tradeoff.
"""

from uuid import uuid4
from pydantic import BaseModel


class Critique(BaseModel):
    """
    Structured feedback produced by stress-testing an architecture against a future.

    Attributes:
        id: Unique identifier (UUID4).
        future: The future_id that produced this critique (e.g. "scaling").
        summary: One-paragraph description of the failure mode.
        risks: Specific risks identified (max 3, enforced by the review prompt).
        required_tradeoff: Statement of the tradeoff that resolves this critique,
            or "Unresolved" if not yet declared.
        resolved: True once a tradeoff has been accepted and recorded.
    """

    id: str
    future: str
    summary: str
    risks: list[str]
    required_tradeoff: str
    resolved: bool = False


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

CRITIQUE_STORE: dict[str, Critique] = {}
"""Global in-memory store keyed by critique ID. Reset on server restart."""


def save_critique(critique: Critique) -> None:
    """Persist a Critique in CRITIQUE_STORE."""
    CRITIQUE_STORE[critique.id] = critique


def get_critique(critique_id: str) -> Critique | None:
    """Retrieve a Critique by ID, or None if not found."""
    return CRITIQUE_STORE.get(critique_id)


def unresolved_critiques() -> list[Critique]:
    """Return all Critiques that have not yet been resolved by a tradeoff."""
    return [c for c in CRITIQUE_STORE.values() if not c.resolved]
