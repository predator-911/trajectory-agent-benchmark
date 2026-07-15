"""Pure metric functions, one per trajectory-evaluation dimension.

Each function takes a Trajectory (and, where needed, a scenario ground-truth
dict) and returns a float in [0, 1] (or a raw count for latency/cost, which
scorer.py normalizes separately).
"""
from __future__ import annotations

from agentic_logistics.evaluation.trajectory import Trajectory

# Legal (from_node, to_node) transitions per the state diagram in
# docs/diagrams/state_machine.mmd. Used to compute the state-transition metric.
LEGAL_TRANSITIONS: set[tuple[str, str]] = {
    ("planner", "risk"),
    ("risk", "carrier_lookup"),
    ("carrier_lookup", "carrier_lookup"),  # self-retry
    ("carrier_lookup", "route_optimizer"),
    ("route_optimizer", "validator"),
    ("validator", "route_optimizer"),  # validator sends back for retry
    ("validator", "execution"),
    ("execution", "execution"),  # self-retry
    ("execution", "audit"),
}


def plan_coherence(trajectory: Trajectory, ground_truth: dict) -> float:
    """How well the actual node sequence matches the expected canonical order.

    Computed as the fraction of positions where the actual sequence (with
    consecutive duplicate node names collapsed, i.e. retries don't count as
    new plan positions) matches the expected order at the same index.
    """
    expected = ground_truth.get("expected_node_order", [])
    if not expected:
        return 1.0
    actual = _collapsed_node_sequence(trajectory)
    # Drop 'planner' from actual since expected_node_order describes the
    # *downstream* pipeline the planner is expected to have planned for.
    actual = [n for n in actual if n != "planner"]
    matches = sum(1 for a, e in zip(actual, expected) if a == e)
    return round(matches / len(expected), 3)


def tool_selection_precision(trajectory: Trajectory, ground_truth: dict) -> float:
    expected_tools = set(ground_truth.get("expected_tools_used", []))
    if not expected_tools:
        return 1.0
    all_calls = [tc for step in trajectory.steps for tc in step.tool_calls]
    if not all_calls:
        return 0.0
    correct = sum(1 for tc in all_calls if tc.tool_name in expected_tools)
    return round(correct / len(all_calls), 3)


def schema_validity_rate(trajectory: Trajectory) -> float:
    all_calls = [tc for step in trajectory.steps for tc in step.tool_calls]
    if not all_calls:
        return 1.0
    valid = sum(1 for tc in all_calls if tc.schema_valid)
    return round(valid / len(all_calls), 3)


def valid_transition_rate(trajectory: Trajectory) -> float:
    sequence = [s.node_name for s in trajectory.steps]
    if len(sequence) < 2:
        return 1.0
    pairs = list(zip(sequence, sequence[1:]))
    valid = sum(1 for pair in pairs if pair in LEGAL_TRANSITIONS)
    return round(valid / len(pairs), 3)


def error_recovery_success_rate(trajectory: Trajectory) -> float:
    """Of steps whose tool call errored, what fraction were followed by a
    successful retry of the same node (rather than escalation/failure)?
    """
    error_steps = [
        (i, s) for i, s in enumerate(trajectory.steps) if any(tc.error for tc in s.tool_calls)
    ]
    if not error_steps:
        return 1.0
    recovered = 0
    for i, s in error_steps:
        for later in trajectory.steps[i + 1 :]:
            if later.node_name == s.node_name:
                if not any(tc.error for tc in later.tool_calls):
                    recovered += 1
                break
    return round(recovered / len(error_steps), 3)


def average_retries(trajectory: Trajectory) -> float:
    return float(len(trajectory.retry_steps()))


def hallucination_rate(trajectory: Trajectory, ground_truth: dict) -> float:
    expected_entities = set(ground_truth.get("expected_entities", []))
    referenced = [e for s in trajectory.steps for e in s.entities_referenced if e]
    if not referenced:
        return 0.0
    hallucinated = [e for e in referenced if e not in expected_entities]
    return round(len(hallucinated) / len(referenced), 3)


def task_completion(trajectory: Trajectory, ground_truth: dict) -> float:
    expected = ground_truth.get("expected_terminal_status")
    return 1.0 if trajectory.final_status == expected else 0.0


def total_latency_ms(trajectory: Trajectory) -> int:
    return trajectory.total_latency_ms()


def estimated_cost(trajectory: Trajectory) -> float:
    """0.0 for mock providers (token_cost_estimate defaults to 0.0 per step).

    Kept as a real, callable formula (sum of per-step token_cost_estimate) so
    that plugging in a real provider that populates token_cost_estimate needs
    no changes here.
    """
    return round(sum(s.token_cost_estimate for s in trajectory.steps), 4)


def _collapsed_node_sequence(trajectory: Trajectory) -> list[str]:
    sequence = [s.node_name for s in trajectory.steps]
    collapsed: list[str] = []
    for n in sequence:
        if not collapsed or collapsed[-1] != n:
            collapsed.append(n)
    return collapsed
