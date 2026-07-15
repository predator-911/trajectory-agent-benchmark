"""Risk node: scores disruption risk; a high score short-circuits straight to escalation."""
from __future__ import annotations

from typing import Callable

from agentic_logistics.config.settings import SYNTHETIC_LATENCY_MS
from agentic_logistics.evaluation.trajectory import Step
from agentic_logistics.graph.nodes._tool_helpers import invoke_and_record
from agentic_logistics.graph.nodes.deps import NodeDeps


def make_risk_node(deps: NodeDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        alert = state["alert"]

        affected_reliability = None
        if alert.affected_carrier_id:
            carrier = deps.carrier_repository.get(alert.affected_carrier_id)
            if carrier is not None:
                affected_reliability = carrier.reliability_score

        decision = deps.provider.decide_tool_call(
            "risk", {**state, "affected_carrier_reliability": affected_reliability}
        )
        result, tool_call, error = invoke_and_record(
            deps.tool_registry, decision.tool_name, decision.arguments
        )

        trajectory = state["trajectory"]
        step = Step(
            step_index=len(trajectory.steps),
            node_name="risk",
            reasoning_trace=decision.rationale,
            tool_calls=[tool_call],
            latency_ms=SYNTHETIC_LATENCY_MS.get("risk", 90),
        )
        trajectory.add_step(step)

        updates = {
            "affected_carrier_reliability": affected_reliability,
            "trajectory": trajectory,
        }
        if error is None:
            updates["risk_assessment"] = result.model_dump()
        return updates

    return node
