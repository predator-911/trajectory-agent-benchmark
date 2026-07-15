"""Execution node: (simulated) execution of the validated reroute.

Distinguishes transient failures (retryable, up to a ceiling) from a final
FAILED status once the ceiling is hit, or immediately for non-transient errors.
"""
from __future__ import annotations

from typing import Callable

from agentic_logistics.config.settings import SYNTHETIC_LATENCY_MS
from agentic_logistics.domain.errors import ExecutionError
from agentic_logistics.evaluation.trajectory import Step
from agentic_logistics.graph.nodes._tool_helpers import invoke_and_record
from agentic_logistics.graph.nodes.deps import NodeDeps


def make_execution_node(deps: NodeDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        retry_counts = dict(state.get("retry_counts", {}))
        attempt = retry_counts.get("execution", 0)

        decision = deps.provider.decide_tool_call("execution", state)
        result, tool_call, error = invoke_and_record(
            deps.tool_registry, decision.tool_name, decision.arguments
        )

        trajectory = state["trajectory"]
        step = Step(
            step_index=len(trajectory.steps),
            node_name="execution",
            reasoning_trace=decision.rationale,
            tool_calls=[tool_call],
            retry_of_step_index=(_previous_execution_step(trajectory) if attempt > 0 else None),
            latency_ms=SYNTHETIC_LATENCY_MS.get("execution", 200),
            entities_referenced=[decision.arguments.get("carrier_id", "")],
        )
        trajectory.add_step(step)

        updates: dict = {"trajectory": trajectory}
        if error is None:
            updates["execution_result"] = result.model_dump()
            updates["_last_error"] = None
        else:
            transient = isinstance(error, ExecutionError) and error.transient
            retry_counts["execution"] = attempt + 1
            updates["retry_counts"] = retry_counts
            updates["_last_error"] = {
                "node": "execution",
                "message": str(error),
                "transient": transient,
            }
        return updates

    return node


def _previous_execution_step(trajectory) -> int | None:
    for s in reversed(trajectory.steps):
        if s.node_name == "execution":
            return s.step_index
    return None
