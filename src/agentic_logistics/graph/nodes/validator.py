"""Validator node: checks the proposed route against business rules before execution."""
from __future__ import annotations

from typing import Callable

from agentic_logistics.config.settings import SYNTHETIC_LATENCY_MS
from agentic_logistics.domain.models import RouteCandidate
from agentic_logistics.evaluation.trajectory import Step
from agentic_logistics.graph.nodes._tool_helpers import invoke_and_record
from agentic_logistics.graph.nodes.deps import NodeDeps


def make_validator_node(deps: NodeDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        decision = deps.provider.decide_tool_call("validator", state)
        route = RouteCandidate(**decision.arguments["route"])
        call_args = {**decision.arguments, "route": route}
        result, tool_call, error = invoke_and_record(
            deps.tool_registry, decision.tool_name, call_args
        )

        trajectory = state["trajectory"]
        step = Step(
            step_index=len(trajectory.steps),
            node_name="validator",
            reasoning_trace=decision.rationale,
            tool_calls=[tool_call],
            latency_ms=SYNTHETIC_LATENCY_MS.get("validator", 80),
            entities_referenced=[route.carrier_id],
        )
        trajectory.add_step(step)

        retry_counts = dict(state.get("retry_counts", {}))
        updates: dict = {"trajectory": trajectory}
        if error is None:
            updates["validation_result"] = result.model_dump()
            if not result.is_valid:
                retry_counts["route_optimizer"] = retry_counts.get("route_optimizer", 0) + 1
                updates["retry_counts"] = retry_counts
        else:
            updates["_last_error"] = {"node": "validator", "message": str(error)}
        return updates

    return node
