"""
In-memory review store.

REVIEW_STORE holds the full lifecycle state for every architecture submitted
in the current server session. It is intentionally in-memory — there is no
persistence between server restarts. For production use, replace this dict
with a proper database (e.g. SQLite via SQLModel, or a cloud store).

Schema for each entry:
    {
        "initial_architecture": str,       # raw text from generate/submit
        "tradeoffs": [                     # appended by declare_tradeoff()
            {
                "critique_id": str,
                "statement": str
            }
        ],
        "critiques": [str],                # list of critique UUIDs
        "final_architecture": str | None   # set by finalize_architecture_tool
    }
"""

REVIEW_STORE: dict[str, dict] = {}
