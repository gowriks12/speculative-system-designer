# Tool API Reference

This document describes every tool exposed by the Speculative System Designer MCP server.

---

## `generate_architecture_tool`

**Type:** Async tool (uses MCP Sampling)

Generate a system architecture constrained by all roots defined in `data/roots.json`.

### Input

| Parameter | Type +| Required | Description |
|---|---|---|---|
| `problem_statement` | string | ✅ | Plain-language description of the system to design. |

### Output

```json
{
  "status": "architecture_generated",
  "architecture_id": "uuid-string",
  "architecture_text": "Full architecture description..."
}
```

### Notes

- The `architecture_id` is required by all subsequent tools.
- The LLM is instructed to explain how its design satisfies each root constraint before providing the final text.
- Internally calls `submit_architecture_tool` to save the result.

---

## `evaluate_architecture_tool`

**Type:** Async tool (uses MCP Sampling + Elicitation)

Run the complete evaluation pipeline: simulate all futures, collect tradeoffs from the user, then finalize.

### Input

| Parameter | Type | Required | Description |
|---|---|---|---|
| `architecture_id` | string | ✅ | UUID from `generate_architecture_tool`. |

### Output

```json
{
  "status": "evaluation_complete",
  "final_architecture": {
    "status": "finalized",
    "final_architecture": "Revised architecture text..."
  }
}
```

### Notes

- The user will be prompted once per future (default: 3 times) to select a tradeoff.
- All tradeoffs must be accepted before finalization proceeds.
- This is the recommended entry point for a full design session.

---

## `simulate_future_tool`

**Type:** Async tool (uses MCP Sampling)

Stress-test a saved architecture against a single future scenario.

### Input

| Parameter | Type | Required | Description |
|---|---|---|---|
| `architecture_id` | string | ✅ | UUID of the architecture to test. |
| `future_id` | string | ✅ | Key from `data/futures.json` (e.g. `"scaling"`, `"security_abuse"`, `"regulatory_compliance"`). |

### Output

```json
{
  "status": "critique_generated",
  "critique": {
    "id": "uuid-string",
    "future": "scaling",
    "summary": "The primary bottleneck will be...",
    "risks": ["Risk one", "Risk two", "Risk three"],
    "required_tradeoff": "Unresolved",
    "resolved": false
  }
}
```

### Error responses

```json
{"status": "error", "reason": "Unknown architecture_id: ..."}
{"status": "error", "reason": "Unknown future_id: ..."}
```

---

## `propose_tradeoff_tool`

**Type:** Async tool (uses MCP Sampling + Elicitation)

Generate three tradeoff options for a critique and ask the user to choose one.

### Input

| Parameter | Type | Required | Description |
|---|---|---|---|
| `architecture_id` | string | ✅ | UUID of the architecture under review. |
| `critique_id` | string | ✅ | UUID of the Critique to resolve (from `simulate_future_tool`). |
| `critique_summary` | string | ✅ | Human-readable summary of the problem. |

### Output

On acceptance:
```json
{
  "status": "tradeoff_declared",
  "selected": {
    "id": "B",
    "statement": "Accept higher operational cost in exchange for...",
    "sacrifice": "Cost predictability",
    "benefit": "Linear scalability"
  }
}
```

On cancellation:
```json
{"status": "cancelled"}
```

### Notes

- Uses **MCP Elicitation** — the client UI will show the three options and wait for user input.
- The accepted tradeoff is immediately recorded via `declare_tradeoff`.

---

## `finalize_architecture_tool`

**Type:** Async tool (uses MCP Sampling)

Produce a revised architecture that concretely reflects all accepted tradeoffs.

### Input

| Parameter | Type | Required | Description |
|---|---|---|---|
| `architecture_id` | string | ✅ | UUID of the architecture to finalize. |

### Output

```json
{
  "status": "finalized",
  "final_architecture": "Revised architecture text incorporating all tradeoffs..."
}
```

### Error responses

```json
{"status": "error", "reason": "Unknown architecture_id: ..."}
{"status": "error", "reason": "No tradeoffs declared. Run evaluate_architecture_tool first."}
```

---

## `submit_architecture_tool`

**Type:** Sync tool

Save a pre-written architecture and receive an `architecture_id`. Use this when you already have an architecture text and want to run it through the evaluation pipeline without using `generate_architecture_tool`.

### Input

| Parameter | Type | Required | Description |
|---|---|---|---|
| `description` | string | ✅ | Full architecture description as plain text. |

### Output

```json
{
  "status": "saved",
  "architecture_id": "uuid-string"
}
```

---

## Resources

The server exposes two MCP Resources that clients can read directly:

| URI | Description |
|---|---|
| `roots://governance` | Full contents of `data/roots.json` |
| `roots://futures` | Full contents of `data/futures.json` |
