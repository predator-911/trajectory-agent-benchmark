"""Route optimizer node: picks the lowest-cost feasible route from candidate carriers."""
from __future__ import annotations

from typing import Callable

from agentic_logistics.config.settings import SYNTHETIC_LATENCY_MS
from agentic_logistics.domain.models import Carrier
from agentic_logistics.evaluation.trajectory import Step
from agentic_logistics.graph.nodes._tool_helpers import invoke_and_record
from agentic_logistics.graph.nodes.deps import NodeDeps


def make_route_optimizer_node(deps: NodeDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        decision = deps.provider.decide_tool_call("route_optimizer", state)
        carriers = [Carrier(**c) for c in decision.arguments.get("carriers", [])]
        call_args = {**decision.arguments, "carriers": carriers}
        result, tool_call, error = invoke_and_record(
            deps.tool_registry, decision.tool_name, call_args
        )

        trajectory = state["trajectory"]
        entities = []
        if error is None:
            chosen, rejected = result
            entities = [chosen.carrier_id] + [r.carrier_id for r in rejected]
        step = Step(
            step_index=len(trajectory.steps),
            node_name="route_optimizer",
            reasoning_trace=decision.rationale,
            tool_calls=[tool_call],
            latency_ms=SYNTHETIC_LATENCY_MS.get("route_optimizer", 180),
            entities_referenced=entities,
        )
        trajectory.add_step(step)

        updates: dict = {"trajectory": trajectory}
        if error is None:
            chosen, rejected = result
            updates["candidate_route"] = chosen.model_dump()
            updates["rejected_alternatives"] = [r.model_dump() for r in rejected]
            updates["_last_error"] = None
        else:
            updates["_last_error"] = {"node": "route_optimizer", "message": str(error)}
        return updates

    return node
