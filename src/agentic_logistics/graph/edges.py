"""Conditional routing logic: pure functions of GraphState -> next-node label.

Kept separate from nodes so branching logic is independently unit-testable,
and so it maps directly onto the state diagram in docs/diagrams/state_machine.mmd.
"""
from __future__ import annotations

# Route labels used as keys in build_graph.py's add_conditional_edges mappings.
PROCEED = "proceed"
RETRY_SELF = "retry_self"
BACK_TO_ROUTE_OPTIMIZER = "back_to_route_optimizer"
ESCALATE_HIGH_RISK = "escalate_high_risk"
ESCALATE_NO_VIABLE_ROUTE = "escalate_no_viable_route"
FAIL_EXECUTION = "fail_execution"


def route_after_risk(state: dict) -> str:
    risk_assessment = state.get("risk_assessment")
    threshold = state.get("settings", {}).get("risk_escalation_threshold", 0.75)
    if risk_assessment and risk_assessment.get("risk_score", 0.0) > threshold:
        return ESCALATE_HIGH_RISK
    return PROCEED


def route_after_carrier_lookup(state: dict) -> str:
    last_error = state.get("_last_error")
    if last_error and last_error.get("node") == "carrier_lookup":
        max_retries = state.get("settings", {}).get("max_retries_carrier_lookup", 2)
        attempts_so_far = state.get("retry_counts", {}).get("carrier_lookup", 0)
        if attempts_so_far <= max_retries:
            return RETRY_SELF
        return ESCALATE_NO_VIABLE_ROUTE
    return PROCEED


def route_after_route_optimizer(state: dict) -> str:
    last_error = state.get("_last_error")
    if last_error and last_error.get("node") == "route_optimizer":
        return ESCALATE_NO_VIABLE_ROUTE
    return PROCEED


def route_after_validator(state: dict) -> str:
    validation_result = state.get("validation_result")
    if validation_result is None:
        return ESCALATE_NO_VIABLE_ROUTE
    if validation_result.get("is_valid"):
        return PROCEED
    max_retries = state.get("settings", {}).get("max_retries_route_optimizer", 2)
    attempts_so_far = state.get("retry_counts", {}).get("route_optimizer", 0)
    if attempts_so_far <= max_retries:
        return BACK_TO_ROUTE_OPTIMIZER
    return ESCALATE_NO_VIABLE_ROUTE


def route_after_execution(state: dict) -> str:
    last_error = state.get("_last_error")
    if last_error and last_error.get("node") == "execution":
        max_retries = state.get("settings", {}).get("max_retries_execution", 1)
        attempts_so_far = state.get("retry_counts", {}).get("execution", 0)
        if last_error.get("transient") and attempts_so_far <= max_retries:
            return RETRY_SELF
        return FAIL_EXECUTION
    return PROCEED
