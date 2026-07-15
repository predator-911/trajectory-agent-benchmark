"""Execution simulator tool: deterministic, seeded, never calls a real carrier API."""
from __future__ import annotations

from agentic_logistics.domain.errors import ExecutionError
from agentic_logistics.domain.models import ExecutionResult


def execution_simulator(
    carrier_id: str,
    alert_id: str,
    force_transient_failure_then_succeed: bool,
    attempt_number: int,
) -> ExecutionResult:
    """Simulate executing a reroute with a specific carrier.

    When force_transient_failure_then_succeed is True, the first attempt
    (attempt_number == 1) raises a transient ExecutionError; subsequent
    attempts succeed. This flag is scenario-driven (via ground truth /
    provider error injection), never randomly generated.
    """
    if force_transient_failure_then_succeed and attempt_number == 1:
        raise ExecutionError(
            f"Simulated transient carrier-booking failure for {carrier_id}",
            transient=True,
        )
    confirmation_id = f"CONF-{alert_id}-{carrier_id}-{attempt_number}"
    return ExecutionResult(executed=True, confirmation_id=confirmation_id)
