"""Unit tests for evaluation metric functions against hand-constructed
toy Trajectory objects with known expected scores.
"""
from __future__ import annotations

from agentic_logistics.evaluation import metrics
from agentic_logistics.evaluation.trajectory import Step, ToolCall, Trajectory


def _step(node_name, step_index, tool_calls=None, entities=None, retry_of=None):
    return Step(
        step_index=step_index,
        node_name=node_name,
        tool_calls=tool_calls or [],
        entities_referenced=entities or [],
        retry_of_step_index=retry_of,
    )


def test_schema_validity_rate_with_one_invalid_of_five():
    steps = []
    for i in range(5):
        valid = i != 2
        tc = ToolCall(tool_name="t", arguments={}, expected_schema_valid=True, schema_valid=valid)
        steps.append(_step("n", i, tool_calls=[tc]))
    traj = Trajectory(scenario_id="s", provider_name="mock", steps=steps)
    assert metrics.schema_validity_rate(traj) == 0.8


def test_schema_validity_rate_with_no_tool_calls_is_perfect():
    traj = Trajectory(scenario_id="s", provider_name="mock", steps=[_step("n", 0)])
    assert metrics.schema_validity_rate(traj) == 1.0


def test_plan_coherence_full_match():
    steps = [_step("risk", 0), _step("carrier_lookup", 1), _step("route_optimizer", 2)]
    traj = Trajectory(scenario_id="s", provider_name="mock", steps=steps)
    gt = {"expected_node_order": ["risk", "carrier_lookup", "route_optimizer"]}
    assert metrics.plan_coherence(traj, gt) == 1.0


def test_plan_coherence_partial_match():
    steps = [_step("risk", 0), _step("route_optimizer", 1)]  # wrong second node
    traj = Trajectory(scenario_id="s", provider_name="mock", steps=steps)
    gt = {"expected_node_order": ["risk", "carrier_lookup"]}
    assert metrics.plan_coherence(traj, gt) == 0.5


def test_hallucination_rate_detects_unknown_entity():
    steps = [_step("carrier_lookup", 0, entities=["CARR-001", "CARR-999"])]
    traj = Trajectory(scenario_id="s", provider_name="mock", steps=steps)
    gt = {"expected_entities": ["CARR-001"]}
    assert metrics.hallucination_rate(traj, gt) == 0.5


def test_hallucination_rate_zero_when_no_entities_referenced():
    steps = [_step("risk", 0)]
    traj = Trajectory(scenario_id="s", provider_name="mock", steps=steps)
    assert metrics.hallucination_rate(traj, {"expected_entities": []}) == 0.0


def test_valid_transition_rate_all_legal():
    steps = [_step("planner", 0), _step("risk", 1), _step("carrier_lookup", 2)]
    traj = Trajectory(scenario_id="s", provider_name="mock", steps=steps)
    assert metrics.valid_transition_rate(traj) == 1.0


def test_valid_transition_rate_detects_illegal_jump():
    steps = [_step("planner", 0), _step("execution", 1)]  # illegal: skips straight to execution
    traj = Trajectory(scenario_id="s", provider_name="mock", steps=steps)
    assert metrics.valid_transition_rate(traj) == 0.0


def test_average_retries_counts_retry_steps():
    steps = [
        _step("carrier_lookup", 0),
        _step("carrier_lookup", 1, retry_of=0),
        _step("carrier_lookup", 2, retry_of=1),
    ]
    traj = Trajectory(scenario_id="s", provider_name="mock", steps=steps)
    assert metrics.average_retries(traj) == 2.0


def test_task_completion_matches_expected_status():
    traj = Trajectory(scenario_id="s", provider_name="mock", steps=[], final_status="SUCCESS")
    assert metrics.task_completion(traj, {"expected_terminal_status": "SUCCESS"}) == 1.0
    assert metrics.task_completion(traj, {"expected_terminal_status": "ESCALATED"}) == 0.0


def test_error_recovery_success_rate_recovers_after_retry():
    error_tc = ToolCall(tool_name="t", arguments={}, expected_schema_valid=True, schema_valid=False, error="boom")
    ok_tc = ToolCall(tool_name="t", arguments={}, expected_schema_valid=True, schema_valid=True)
    steps = [
        _step("carrier_lookup", 0, tool_calls=[error_tc]),
        _step("carrier_lookup", 1, tool_calls=[ok_tc], retry_of=0),
    ]
    traj = Trajectory(scenario_id="s", provider_name="mock", steps=steps)
    assert metrics.error_recovery_success_rate(traj) == 1.0
