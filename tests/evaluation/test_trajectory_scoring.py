"""Evaluation-tier test: run one scenario end-to-end through the real graph
and confirm a well-formed ScoreCard is produced with all dimensions populated.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from agentic_logistics.config.settings import DEFAULT_SETTINGS
from agentic_logistics.domain.models import TelemetryAlert
from agentic_logistics.evaluation.scorer import compute_scorecard
from agentic_logistics.graph.build_graph import run

SCENARIOS_DIR = Path(__file__).resolve().parents[2] / "scenarios"


def test_scorecard_has_all_ten_dimensions_populated():
    with open(SCENARIOS_DIR / "scenario_01_port_congestion.json") as f:
        scenario = json.load(f)
    alert = TelemetryAlert(**scenario["alert"])
    settings = replace(DEFAULT_SETTINGS, write_audit_log_file=False)

    trajectory = run(alert, provider_name="mock", settings=settings)
    scorecard = compute_scorecard(trajectory, scenario["ground_truth"])

    assert scorecard.final_status == "SUCCESS"
    for field in [
        "plan_coherence",
        "tool_selection_precision",
        "schema_validity_rate",
        "valid_transition_rate",
        "error_recovery_success_rate",
        "average_retries",
        "hallucination_rate",
        "task_completion",
        "total_latency_ms",
        "estimated_cost",
        "composite_score",
    ]:
        assert getattr(scorecard, field) is not None

    assert 0.0 <= scorecard.composite_score <= 4.0


def test_composite_score_matches_manual_recomputation():
    with open(SCENARIOS_DIR / "scenario_01_port_congestion.json") as f:
        scenario = json.load(f)
    alert = TelemetryAlert(**scenario["alert"])
    settings = replace(DEFAULT_SETTINGS, write_audit_log_file=False)
    trajectory = run(alert, provider_name="mock", settings=settings)
    sc = compute_scorecard(trajectory, scenario["ground_truth"])

    expected = round(
        0.25 * sc.rubric_task_completion
        + 0.25 * sc.rubric_error_recovery
        + 0.18 * sc.rubric_tool_correctness
        + 0.18 * sc.rubric_state_transitions
        + 0.07 * sc.rubric_hallucination
        + 0.07 * sc.rubric_planning,
        3,
    )
    assert sc.composite_score == expected
