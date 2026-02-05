from pydantic import BaseModel
from typing import List
from uuid import uuid4

class Architecture(BaseModel):
    id: str
    description: str
    status: str  # submitted | rejected | under_review | approved
    root_violations: List[str] = []

def create_architecture(description: str) -> Architecture:
    return Architecture(
        id=str(uuid4()),
        description=description,
        status="submitted",
        root_violations=[]
    )
