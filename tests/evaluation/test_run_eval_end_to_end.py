"""Evaluation-tier test: running the full harness across all shipped scenarios
produces a well-formed report without exceptions, for both providers.
"""
from __future__ import annotations

from agentic_logistics.evaluation.run_eval import run_all


def test_run_all_produces_a_scorecard_per_scenario_per_provider():
    scorecards = run_all(providers=("mock", "mock_flaky"))
    assert len(scorecards) == 5 * 2
    scenario_ids = {sc.scenario_id for sc in scorecards}
    assert len(scenario_ids) == 5
    assert all(sc.final_status in ("SUCCESS", "ESCALATED", "FAILED") for sc in scorecards)


def test_run_all_never_produces_a_silent_failure_on_shipped_scenarios():
    scorecards = run_all(providers=("mock", "mock_flaky"))
    # None of the shipped scenarios are designed to hit unsupervised FAILED --
    # only the escalation path (scenario 5) and successes are expected.
    assert all(sc.final_status != "FAILED" for sc in scorecards)
