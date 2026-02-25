from server.resources.roots import load_roots, format_roots_for_prompt
from server.resources.futures import *

FUTURES = load_futures()
ROOTS = load_roots()

def initial_architecture_prompt(system_description):
    return f"""You are a senior systems architect.

    Generate an **Initial Architecture** for the system below. It must satisfy every root constraint.

    ## System
    {system_description}

    ## Root Constraints
    {format_roots_for_prompt(ROOTS)}

    Produce a Markdown document with: Overview, Components, Data Flow, Key Design Decisions, and how each root constraint is met. 
    Keep it conscise and within 10 sentences."""



def simulating_future(future_id, architecture):
    return f"""You are a systems architect running a speculative simulation.

    Stress-test the architecture against the future scenario. Identify what holds, degrades, and breaks.

    ## Architecture
    {architecture}

    # ## Future: {future_id}
    # {future_prompt(FUTURES.get(future_id))}

    # ## Root Constraints (must never be violated)
    # {format_roots_for_prompt(ROOTS)}

    # Produce a Markdown report titled "Simulation: {future_id}" covering: what Holds, Degrades, Breaks, any Root Constraint Violations, and Adaptation Suggestions."""



def pickup_issues(architecture, simulated_results):
    return f"""You are a senior systems architect doing cross-future analysis.

    ## Original Architecture
    {architecture}

    ## Simulation Results
    {simulated_results}

    ## Root Constraints
    {format_roots_for_prompt(ROOTS)}

    Produce a Markdown report titled "Tradeoffs & Issues" covering: Recurring Failures, Architectural Tensions, Constraint Fragility, Opportunity Areas, and Top Priority Issues to fix."""


def final_architecture_prompt(system_description, initial_architecture, tradeoffs_and_issues):
    f"""You are a senior systems architect producing a final battle-tested design.

    ## System
    {system_description}

    ## Initial Architecture
    {initial_architecture}

    ## Tradeoffs & Issues to Address
    {tradeoffs_and_issues}

    ## Root Constraints
    {format_roots_for_prompt(ROOTS)}

    Produce a comprehensive Markdown document titled "Final Architecture" with: what changed and why, updated Components, Resilience Mechanisms per future, and Remaining Risks."""

