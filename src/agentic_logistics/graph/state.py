"""The shared, typed state threaded through every node in the LangGraph pipeline.

Nodes read what they need from GraphState and write their results back into
it. Nodes never communicate with each other directly -- only through this
object and the conditional edges in edges.py.
"""
from __future__ import annotations

from typing import Any, Optional, TypedDict

from agentic_logistics.domain.models import (
    RiskAssessment,
    TelemetryAlert,
)
from agentic_logistics.evaluation.trajectory import Trajectory


class GraphState(TypedDict, total=False):
    alert: TelemetryAlert
    settings: dict[str, Any]

    plan_rationale: str
    plan_used_default_fallback: bool

    risk_assessment: Optional[RiskAssessment]

    candidate_carriers: list[dict]  # serialized Carrier dicts (JSON-safe for LangGraph state)
    affected_carrier_reliability: Optional[float]

    candidate_route: Optional[dict]  # serialized RouteCandidate
    rejected_alternatives: list[dict]

    validation_result: Optional[dict]  # serialized ValidationResult

    execution_result: Optional[dict]  # serialized ExecutionResult

    retry_counts: dict[str, int]

    trajectory: Trajectory

    final_status: str
    escalation_reason: Optional[str]


def new_initial_state(alert: TelemetryAlert, settings: dict[str, Any]) -> GraphState:
    """Construct the initial GraphState for a fresh run (the "TelemetryIngest" step)."""
    return GraphState(
        alert=alert,
        settings=settings,
        plan_rationale="",
        plan_used_default_fallback=False,
        risk_assessment=None,
        candidate_carriers=[],
        affected_carrier_reliability=None,
        candidate_route=None,
        rejected_alternatives=[],
        validation_result=None,
        execution_result=None,
        retry_counts={},
        trajectory=Trajectory(scenario_id=alert.alert_id, provider_name="", steps=[]),
        final_status="IN_PROGRESS",
        escalation_reason=None,
    )
