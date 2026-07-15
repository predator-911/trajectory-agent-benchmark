"""Flaky variant of MockProvider used to deterministically exercise
retry and error-recovery paths during evaluation.

Error injection is targeted and scenario-driven via `alert.extra["inject_failures"]`,
never uniformly random -- this keeps regression tests stable and meaningful.
Recognized keys in `inject_failures`:
    "carrier_lookup": "malformed_then_ok"
        -> first carrier_lookup tool call is missing a required argument
           (schema-invalid); the retry succeeds.
    "execution": "transient_then_ok"
        -> first execution attempt raises a transient ExecutionError inside
           the tool itself (via force_transient_failure_then_succeed=True);
           the retry succeeds.
"""
from __future__ import annotations

from typing import Any

from agentic_logistics.domain.models import TelemetryAlert
from agentic_logistics.ports.model_provider import ToolCallDecision

from .mock_provider import MockProvider


class MockProviderFlaky(MockProvider):
    """MockProvider with deterministic, scenario-targeted error injection."""

    name = "mock_flaky"

    def decide_tool_call(self, node_name: str, state: dict[str, Any]) -> ToolCallDecision:
        alert: TelemetryAlert = state["alert"]
        inject = alert.extra.get("inject_failures", {})
        retry_counts = state.get("retry_counts", {})

        if node_name == "carrier_lookup" and inject.get("carrier_lookup") == "malformed_then_ok":
            if retry_counts.get("carrier_lookup", 0) == 0:
                # Deliberately omit the required 'destination_region' argument
                # to trigger SchemaValidationError at the tool-registry boundary.
                return ToolCallDecision(
                    tool_name="carrier_lookup",
                    arguments={
                        "origin_region": alert.origin_region,
                        "exclude_carrier_id": alert.affected_carrier_id,
                    },
                    rationale="(injected fault) Attempting carrier lookup with incomplete arguments.",
                )
            # Retry: fall through to the correct, well-formed call below.

        if node_name == "execution" and inject.get("execution") == "transient_then_ok":
            attempt_number = retry_counts.get("execution", 0) + 1
            route = state.get("candidate_route")
            return ToolCallDecision(
                tool_name="execution_simulator",
                arguments={
                    "carrier_id": route["carrier_id"] if route else "UNKNOWN",
                    "alert_id": alert.alert_id,
                    "force_transient_failure_then_succeed": True,
                    "attempt_number": attempt_number,
                },
                rationale="Execute the validated reroute (transient failure possible on first attempt).",
            )

        return super().decide_tool_call(node_name, state)
