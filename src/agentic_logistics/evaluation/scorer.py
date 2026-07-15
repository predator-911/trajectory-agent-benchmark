"""Aggregates raw metrics into the 0-4 rubric scores and the weighted composite
score described in docs/evaluation_framework.md.
"""
from __future__ import annotations

from pydantic import BaseModel

from agentic_logistics.evaluation import metrics
from agentic_logistics.evaluation.trajectory import Trajectory


class ScoreCard(BaseModel):
    scenario_id: str
    provider_name: str
    final_status: str

    # Raw metric values (0-1 unless noted)
    plan_coherence: float
    tool_selection_precision: float
    schema_validity_rate: float
    valid_transition_rate: float
    error_recovery_success_rate: float
    average_retries: float
    hallucination_rate: float
    task_completion: float
    total_latency_ms: int
    estimated_cost: float

    # 0-4 rubric scores
    rubric_planning: float
    rubric_tool_selection: float
    rubric_tool_correctness: float
    rubric_state_transitions: float
    rubric_error_recovery: float
    rubric_hallucination: float
    rubric_task_completion: float

    composite_score: float


def _to_rubric(value: float) -> float:
    """Linear scale a [0,1] metric to the [0,4] rubric range."""
    return round(max(0.0, min(1.0, value)) * 4, 2)


def compute_scorecard(trajectory: Trajectory, ground_truth: dict) -> ScoreCard:
    plan_c = metrics.plan_coherence(trajectory, ground_truth)
    tool_sel = metrics.tool_selection_precision(trajectory, ground_truth)
    schema_valid = metrics.schema_validity_rate(trajectory)
    transitions = metrics.valid_transition_rate(trajectory)
    recovery = metrics.error_recovery_success_rate(trajectory)
    retries = metrics.average_retries(trajectory)
    hallucination = metrics.hallucination_rate(trajectory, ground_truth)
    completion = metrics.task_completion(trajectory, ground_truth)
    latency = metrics.total_latency_ms(trajectory)
    cost = metrics.estimated_cost(trajectory)

    rubric_planning = _to_rubric(plan_c)
    rubric_tool_selection = _to_rubric(tool_sel)
    rubric_tool_correctness = _to_rubric(schema_valid)
    rubric_state_transitions = _to_rubric(transitions)
    rubric_error_recovery = _to_rubric(recovery)
    rubric_hallucination = _to_rubric(1.0 - hallucination)
    rubric_task_completion = _to_rubric(completion)

    # Weighted composite (0-4 scale). Latency/cost are informational-only in
    # this offline-mock context (both are ~0 for the mock providers) and are
    # therefore excluded from the composite rather than padded with a
    # meaningless constant; they are still reported in full on the ScoreCard.
    composite = round(
        0.25 * rubric_task_completion
        + 0.25 * rubric_error_recovery
        + 0.18 * rubric_tool_correctness
        + 0.18 * rubric_state_transitions
        + 0.07 * rubric_hallucination
        + 0.07 * rubric_planning,
        3,
    )

    return ScoreCard(
        scenario_id=trajectory.scenario_id,
        provider_name=trajectory.provider_name,
        final_status=trajectory.final_status,
        plan_coherence=plan_c,
        tool_selection_precision=tool_sel,
        schema_validity_rate=schema_valid,
        valid_transition_rate=transitions,
        error_recovery_success_rate=recovery,
        average_retries=retries,
        hallucination_rate=hallucination,
        task_completion=completion,
        total_latency_ms=latency,
        estimated_cost=cost,
        rubric_planning=rubric_planning,
        rubric_tool_selection=rubric_tool_selection,
        rubric_tool_correctness=rubric_tool_correctness,
        rubric_state_transitions=rubric_state_transitions,
        rubric_error_recovery=rubric_error_recovery,
        rubric_hallucination=rubric_hallucination,
        rubric_task_completion=rubric_task_completion,
        composite_score=composite,
    )
