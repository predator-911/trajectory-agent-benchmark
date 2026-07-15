"""Carrier lookup node: finds viable carriers for the alert's lane.

May be entered multiple times (self-retry edge) -- retry_counts['carrier_lookup']
tracks how many attempts have been made so edges.py can decide whether to
retry again or escalate.
"""
from __future__ import annotations

from typing import Callable

from agentic_logistics.config.settings import SYNTHETIC_LATENCY_MS
from agentic_logistics.evaluation.trajectory import Step
from agentic_logistics.graph.nodes._tool_helpers import invoke_and_record
from agentic_logistics.graph.nodes.deps import NodeDeps


def make_carrier_lookup_node(deps: NodeDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        retry_counts = dict(state.get("retry_counts", {}))
        attempt = retry_counts.get("carrier_lookup", 0)

        decision = deps.provider.decide_tool_call("carrier_lookup", state)
        # Bind the actual repository object for the tool call (not JSON-safe,
        # so it is passed alongside the provider-decided arguments rather than
        # stored in state).
        call_args = {"repository": deps.carrier_repository, **decision.arguments}
        result, tool_call, error = invoke_and_record(
            deps.tool_registry, decision.tool_name, call_args
        )

        trajectory = state["trajectory"]
        step = Step(
            step_index=len(trajectory.steps),
            node_name="carrier_lookup",
            reasoning_trace=decision.rationale,
            tool_calls=[tool_call],
            retry_of_step_index=(_previous_carrier_lookup_step(trajectory) if attempt > 0 else None),
            latency_ms=SYNTHETIC_LATENCY_MS.get("carrier_lookup", 150),
            entities_referenced=[c.carrier_id for c in result] if error is None else [],
        )
        trajectory.add_step(step)

        updates: dict = {"trajectory": trajectory}
        if error is None:
            updates["candidate_carriers"] = [c.model_dump() for c in result]
            updates["_last_error"] = None
        else:
            retry_counts["carrier_lookup"] = attempt + 1
            updates["retry_counts"] = retry_counts
            updates["_last_error"] = {"node": "carrier_lookup", "message": str(error)}
        return updates

    return node


def _previous_carrier_lookup_step(trajectory) -> int | None:
    for s in reversed(trajectory.steps):
        if s.node_name == "carrier_lookup":
            return s.step_index
    return None
