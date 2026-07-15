"""Regression tests: lock in the expected composite score for every
(scenario, provider) pair as of this generation.

Any future change to a node, tool, or metric that shifts one of these
numbers must be a deliberate, reviewed decision -- not silent drift. If a
change legitimately improves behavior, update GOLDEN_SCORES intentionally
in the same commit/PR as the change that caused the shift, with a note
explaining why.
"""
from __future__ import annotations

import pytest

from agentic_logistics.evaluation.run_eval import run_all

GOLDEN_SCORES: dict[tuple[str, str], float] = {
    ("ALERT-001", "mock"): 4.0,
    ("ALERT-001", "mock_flaky"): 4.0,
    ("ALERT-002", "mock"): 4.0,
    ("ALERT-002", "mock_flaky"): 3.879,
    ("ALERT-003", "mock"): 4.0,
    ("ALERT-003", "mock_flaky"): 4.0,
    ("ALERT-004", "mock"): 4.0,
    ("ALERT-004", "mock_flaky"): 4.0,
    ("ALERT-005", "mock"): 3.0,
    ("ALERT-005", "mock_flaky"): 3.0,
}

GOLDEN_STATUS: dict[tuple[str, str], str] = {
    ("ALERT-001", "mock"): "SUCCESS",
    ("ALERT-001", "mock_flaky"): "SUCCESS",
    ("ALERT-002", "mock"): "SUCCESS",
    ("ALERT-002", "mock_flaky"): "SUCCESS",
    ("ALERT-003", "mock"): "SUCCESS",
    ("ALERT-003", "mock_flaky"): "SUCCESS",
    ("ALERT-004", "mock"): "SUCCESS",
    ("ALERT-004", "mock_flaky"): "SUCCESS",
    ("ALERT-005", "mock"): "ESCALATED",
    ("ALERT-005", "mock_flaky"): "ESCALATED",
}

TOLERANCE = 0.01


@pytest.fixture(scope="module")
def scorecards():
    return run_all(providers=("mock", "mock_flaky"))


def test_golden_composite_scores_have_not_drifted(scorecards):
    for sc in scorecards:
        key = (sc.scenario_id, sc.provider_name)
        assert key in GOLDEN_SCORES, f"No golden score recorded for {key} -- add one deliberately."
        expected = GOLDEN_SCORES[key]
        assert abs(sc.composite_score - expected) <= TOLERANCE, (
            f"Composite score for {key} drifted: expected {expected}, got {sc.composite_score}. "
            "If this is an intentional improvement, update GOLDEN_SCORES with a note explaining why."
        )


def test_golden_final_statuses_have_not_drifted(scorecards):
    for sc in scorecards:
        key = (sc.scenario_id, sc.provider_name)
        expected_status = GOLDEN_STATUS[key]
        assert sc.final_status == expected_status, (
            f"Final status for {key} drifted: expected {expected_status}, got {sc.final_status}."
        )
