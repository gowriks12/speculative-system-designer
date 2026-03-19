from typing import TypedDict, Optional, List


class DesignState(TypedDict):
    problem_statement: str
    run_evaluation: bool           # True = simulate futures; False = skip to END after draw_initial
    architecture_id: Optional[str]
    architecture_text: Optional[str]
    critiques: List[dict]          # [{id, future, summary, risks}]
    tradeoffs: List[dict]          # [{critique_id, selected_option}]
    final_architecture: Optional[str]
    current_future_index: int      # tracks progress through the futures loop
    future_ids: List[str]          # fetched from the SSD server at startup
    initial_diagram_url: Optional[str]   # Excalidraw share URL — set by draw_initial
    final_diagram_url: Optional[str]     # Excalidraw share URL — set by draw_final
