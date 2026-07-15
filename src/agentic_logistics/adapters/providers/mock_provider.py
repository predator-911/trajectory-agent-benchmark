"""Deterministic, seeded, rule-based mock model provider.

This is the ONLY provider actually invoked at runtime by default. It is a
pure function of (node_name, state) with no unseeded randomness and no
wall-clock-dependent branching -- running the same scenario twice must
produce byte-identical trajectories (excluding timestamps). This determinism
is what makes the regression test tier meaningful.
"""
from __future__ import annotations

from typing import Any

from agentic_logistics.domain.models import TelemetryAlert
from agentic_logistics.ports.model_provider import ModelProvider, PlanResult, ToolCallDecision

# The fixed pipeline order this system always plans for. The Planner's job in
# this deterministic mock is to *confirm* this canonical order applies to the
# given alert (real frontier vs. open models would be scored on whether they
# reconstruct this same order from the tool/task description alone).
_CANONICAL_ORDER = [
    "risk",
    "carrier_lookup",
    "route_optimizer",
    "validator",
    "execution",
    "audit",
]


class MockProvider(ModelProvider):
    """Deterministic rule-based provider. Default runtime provider."""

    name = "mock"

    def __init__(self, seed: int = 42) -> None:
        # Seed is accepted for interface symmetry with real providers and to
        # make determinism explicit, but this provider uses no randomness.
        self.seed = seed

    def plan(self, alert: TelemetryAlert) -> PlanResult:
        used_default_fallback = alert.severity is None
        rationale = (
            f"Alert '{alert.alert_id}' of type '{alert.alert_type}' requires the "
            f"standard reroute pipeline: {' -> '.join(_CANONICAL_ORDER)}."
        )
        if used_default_fallback:
            rationale += " Severity was not provided; proceeding with a safe default rather than fabricating one."
        return PlanResult(
            ordered_nodes=list(_CANONICAL_ORDER),
            rationale=rationale,
            used_default_fallback=used_default_fallback,
        )

    def decide_tool_call(self, node_name: str, state: dict[str, Any]) -> ToolCallDecision:
        alert: TelemetryAlert = state["alert"]

        if node_name == "risk":
            affected = state.get("affected_carrier_reliability")
            return ToolCallDecision(
                tool_name="risk_scorer",
                arguments={
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "affected_carrier_reliability": affected,
                },
                rationale="Score disruption risk from alert type, severity, and carrier history.",
            )

        if node_name == "carrier_lookup":
            return ToolCallDecision(
                tool_name="carrier_lookup",
                arguments={
                    "origin_region": alert.origin_region,
                    "destination_region": alert.destination_region,
                    "exclude_carrier_id": alert.affected_carrier_id,
                },
                rationale="Look up carriers servicing this lane, excluding the affected carrier.",
            )

        if node_name == "route_optimizer":
            carriers = state.get("candidate_carriers", [])
            return ToolCallDecision(
                tool_name="route_optimizer",
                arguments={
                    "carriers": carriers,
                    "origin_region": alert.origin_region,
                    "destination_region": alert.destination_region,
                    "max_transit_hours": state.get("max_transit_hours", 72.0),
                },
                rationale="Select the lowest-cost carrier meeting the transit-time constraint.",
            )

        if node_name == "validator":
            route = state.get("candidate_route")
            return ToolCallDecision(
                tool_name="route_validator",
                arguments={
                    "route": route,
                    "max_transit_hours": state.get("max_transit_hours", 72.0),
                },
                rationale="Validate the proposed route against business rules before execution.",
            )

        if node_name == "execution":
            route = state.get("candidate_route")
            attempt_number = state.get("retry_counts", {}).get("execution", 0) + 1
            return ToolCallDecision(
                tool_name="execution_simulator",
                arguments={
                    "carrier_id": route["carrier_id"] if route else "UNKNOWN",
                    "alert_id": alert.alert_id,
                    "force_transient_failure_then_succeed": False,
                    "attempt_number": attempt_number,
                },
                rationale="Execute the validated reroute with the chosen carrier.",
            )

        raise ValueError(f"MockProvider has no tool-call rule for node '{node_name}'")
