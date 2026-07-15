"""Composition root: the ONLY place a concrete ModelProvider adapter is chosen.

Exposes a single `run(alert, provider_name, settings) -> Trajectory` function
used by both the CLI demo and the evaluation harness. Swapping providers is a
one-line change to `_build_provider()` plus a new adapter class -- nothing
else in this file, or anywhere else in the codebase, needs to change.
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from agentic_logistics.adapters.data.carrier_repository_json import JsonCarrierRepository
from agentic_logistics.adapters.providers.claude_provider_stub import ClaudeProviderStub
from agentic_logistics.adapters.providers.mock_provider import MockProvider
from agentic_logistics.adapters.providers.mock_provider_flaky import MockProviderFlaky
from agentic_logistics.adapters.providers.ollama_provider_stub import OllamaProviderStub
from agentic_logistics.adapters.providers.openai_provider_stub import OpenAIProviderStub
from agentic_logistics.config.settings import DEFAULT_SETTINGS, Settings
from agentic_logistics.domain.models import TelemetryAlert
from agentic_logistics.evaluation.trajectory import Trajectory
from agentic_logistics.graph import edges
from agentic_logistics.graph.nodes.audit import make_audit_node
from agentic_logistics.graph.nodes.carrier_lookup import make_carrier_lookup_node
from agentic_logistics.graph.nodes.deps import NodeDeps
from agentic_logistics.graph.nodes.execution import make_execution_node
from agentic_logistics.graph.nodes.planner import make_planner_node
from agentic_logistics.graph.nodes.risk import make_risk_node
from agentic_logistics.graph.nodes.route_optimizer import make_route_optimizer_node
from agentic_logistics.graph.nodes.validator import make_validator_node
from agentic_logistics.graph.state import GraphState, new_initial_state
from agentic_logistics.ports.model_provider import ModelProvider
from agentic_logistics.tools.carrier_lookup import carrier_lookup
from agentic_logistics.tools.execution_simulator import execution_simulator
from agentic_logistics.tools.registry import ToolRegistry
from agentic_logistics.tools.risk_scorer import risk_scorer
from agentic_logistics.tools.route_optimizer import route_optimizer
from agentic_logistics.tools.route_validator import route_validator

_PROVIDER_FACTORY = {
    "mock": lambda: MockProvider(),
    "mock_flaky": lambda: MockProviderFlaky(),
    "claude": lambda: ClaudeProviderStub(),
    "openai": lambda: OpenAIProviderStub(),
    "ollama": lambda: OllamaProviderStub(),
}


def _build_provider(provider_name: str) -> ModelProvider:
    factory = _PROVIDER_FACTORY.get(provider_name)
    if factory is None:
        raise ValueError(
            f"Unknown provider '{provider_name}'. Available: {sorted(_PROVIDER_FACTORY)}"
        )
    return factory()


def _build_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        "risk_scorer",
        risk_scorer,
        schema={"alert_type": str, "severity": (str, type(None)), "affected_carrier_reliability": (float, type(None))},
        required={"alert_type"},
    )
    registry.register(
        "carrier_lookup",
        carrier_lookup,
        schema={"repository": object, "origin_region": str, "destination_region": str, "exclude_carrier_id": (str, type(None))},
        required={"repository", "origin_region", "destination_region"},
    )
    registry.register(
        "route_optimizer",
        route_optimizer,
        schema={"carriers": list, "origin_region": str, "destination_region": str, "max_transit_hours": float},
        required={"carriers", "origin_region", "destination_region", "max_transit_hours"},
    )
    registry.register(
        "route_validator",
        route_validator,
        schema={"route": object, "max_transit_hours": float},
        required={"route", "max_transit_hours"},
    )
    registry.register(
        "execution_simulator",
        execution_simulator,
        schema={"carrier_id": str, "alert_id": str, "force_transient_failure_then_succeed": bool, "attempt_number": int},
        required={"carrier_id", "alert_id", "force_transient_failure_then_succeed", "attempt_number"},
    )
    return registry


def _make_terminal_node(status: str, reason: str):
    def node(state: dict) -> dict:
        trajectory = state["trajectory"]
        trajectory.final_status = status
        return {"final_status": status, "escalation_reason": reason, "trajectory": trajectory}

    return node


def build_compiled_graph(deps: NodeDeps):
    """Assemble the 8-stage pipeline (Planner..Audit, plus terminal nodes) into a compiled LangGraph app."""
    graph = StateGraph(GraphState)

    graph.add_node("planner", make_planner_node(deps))
    graph.add_node("risk", make_risk_node(deps))
    graph.add_node("carrier_lookup", make_carrier_lookup_node(deps))
    graph.add_node("route_optimizer", make_route_optimizer_node(deps))
    graph.add_node("validator", make_validator_node(deps))
    graph.add_node("execution", make_execution_node(deps))
    graph.add_node("audit", make_audit_node(deps))

    graph.add_node(
        "escalate_high_risk",
        _make_terminal_node("ESCALATED", "risk_score exceeded escalation threshold"),
    )
    graph.add_node(
        "escalate_no_viable_route",
        _make_terminal_node("ESCALATED", "no viable carrier/route could be constructed"),
    )
    graph.add_node(
        "fail_execution",
        _make_terminal_node("FAILED", "execution failed after exhausting retries"),
    )

    graph.set_entry_point("planner")
    graph.add_edge("planner", "risk")

    graph.add_conditional_edges(
        "risk",
        edges.route_after_risk,
        {edges.PROCEED: "carrier_lookup", edges.ESCALATE_HIGH_RISK: "escalate_high_risk"},
    )
    graph.add_conditional_edges(
        "carrier_lookup",
        edges.route_after_carrier_lookup,
        {
            edges.PROCEED: "route_optimizer",
            edges.RETRY_SELF: "carrier_lookup",
            edges.ESCALATE_NO_VIABLE_ROUTE: "escalate_no_viable_route",
        },
    )
    graph.add_conditional_edges(
        "route_optimizer",
        edges.route_after_route_optimizer,
        {edges.PROCEED: "validator", edges.ESCALATE_NO_VIABLE_ROUTE: "escalate_no_viable_route"},
    )
    graph.add_conditional_edges(
        "validator",
        edges.route_after_validator,
        {
            edges.PROCEED: "execution",
            edges.BACK_TO_ROUTE_OPTIMIZER: "route_optimizer",
            edges.ESCALATE_NO_VIABLE_ROUTE: "escalate_no_viable_route",
        },
    )
    graph.add_conditional_edges(
        "execution",
        edges.route_after_execution,
        {
            edges.PROCEED: "audit",
            edges.RETRY_SELF: "execution",
            edges.FAIL_EXECUTION: "fail_execution",
        },
    )

    graph.add_edge("audit", END)
    graph.add_edge("escalate_high_risk", END)
    graph.add_edge("escalate_no_viable_route", END)
    graph.add_edge("fail_execution", END)

    return graph.compile()


def run(
    alert: TelemetryAlert,
    provider_name: str = "mock",
    settings: Settings = DEFAULT_SETTINGS,
) -> Trajectory:
    """Run one alert through the full pipeline and return the resulting Trajectory.

    This is the single public entrypoint used by both cli.py and the
    evaluation harness (evaluation/run_eval.py).
    """
    provider = _build_provider(provider_name)
    tool_registry = _build_tool_registry()
    carrier_repository = JsonCarrierRepository()

    deps = NodeDeps(
        provider=provider,
        tool_registry=tool_registry,
        carrier_repository=carrier_repository,
        settings=settings.__dict__,
    )
    app = build_compiled_graph(deps)

    initial_state = new_initial_state(alert, settings.__dict__)
    initial_state["trajectory"].provider_name = provider.name

    final_state: dict[str, Any] = app.invoke(initial_state, config={"recursion_limit": 50})
    trajectory: Trajectory = final_state["trajectory"]
    trajectory.final_status = final_state.get("final_status", "IN_PROGRESS")
    return trajectory
