"""Planner node: asks the provider for the ordered plan of downstream nodes."""
from __future__ import annotations

from typing import Callable

from agentic_logistics.evaluation.trajectory import Step
from agentic_logistics.graph.nodes.deps import NodeDeps

from agentic_logistics.config.settings import SYNTHETIC_LATENCY_MS


def make_planner_node(deps: NodeDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        alert = state["alert"]
        plan = deps.provider.plan(alert)

        trajectory = state["trajectory"]
        step = Step(
            step_index=len(trajectory.steps),
            node_name="planner",
            reasoning_trace=plan.rationale,
            latency_ms=SYNTHETIC_LATENCY_MS.get("planner", 100),
        )
        trajectory.add_step(step)

        return {
            "plan_rationale": plan.rationale,
            "plan_used_default_fallback": plan.used_default_fallback,
            "trajectory": trajectory,
        }

    return node
