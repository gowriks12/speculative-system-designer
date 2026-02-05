from pydantic import BaseModel
from typing import List
from uuid import uuid4

class Critique(BaseModel):
    id: str
    future: str
    summary: str
    risks: List[str]
    required_tradeoff: str
    resolved: bool = False

def create_scaling_critique(risks: List[str]) -> Critique:
    return Critique(
        id=str(uuid4()),
        future="scaling",
        summary="Architecture shows stress under increased load.",
        risks=risks,
        required_tradeoff="Scaling tradeoff not yet declared."
    )
