"""CLI entrypoint.

Subcommands:
    demo   - run one scenario through the pipeline and pretty-print the trajectory
    eval   - run the full evaluation harness (delegates to evaluation/run_eval.py)
    graph  - print the compiled graph's node/edge structure
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agentic_logistics.config.settings import DEFAULT_SETTINGS
from agentic_logistics.domain.models import TelemetryAlert
from agentic_logistics.graph.build_graph import build_compiled_graph, run
from agentic_logistics.graph.nodes.deps import NodeDeps

SCENARIOS_DIR = Path(__file__).resolve().parents[2] / "scenarios"


def cmd_demo(args: argparse.Namespace) -> None:
    scenario_path = SCENARIOS_DIR / args.scenario
    with open(scenario_path, "r", encoding="utf-8") as f:
        scenario = json.load(f)
    alert = TelemetryAlert(**scenario["alert"])

    trajectory = run(alert, provider_name=args.provider, settings=DEFAULT_SETTINGS)

    print(f"Scenario: {scenario_path.name}")
    print(f"Provider: {trajectory.provider_name}")
    print(f"Final status: {trajectory.final_status}")
    print("Trajectory:")
    for step in trajectory.steps:
        print(f"  [{step.step_index}] {step.node_name} ({step.latency_ms}ms)")
        if step.reasoning_trace:
            print(f"        reasoning: {step.reasoning_trace}")
        for tc in step.tool_calls:
            status = "OK" if tc.error is None else f"ERROR: {tc.error}"
            print(f"        tool_call: {tc.tool_name}({tc.arguments}) -> {status}")


def cmd_eval(args: argparse.Namespace) -> None:
    from agentic_logistics.evaluation.run_eval import main as eval_main

    eval_main()


def cmd_graph(args: argparse.Namespace) -> None:
    from agentic_logistics.adapters.data.carrier_repository_json import JsonCarrierRepository
    from agentic_logistics.adapters.providers.mock_provider import MockProvider
    from agentic_logistics.graph.build_graph import _build_tool_registry

    deps = NodeDeps(
        provider=MockProvider(),
        tool_registry=_build_tool_registry(),
        carrier_repository=JsonCarrierRepository(),
        settings=DEFAULT_SETTINGS.__dict__,
    )
    app = build_compiled_graph(deps)
    try:
        print(app.get_graph().draw_mermaid())
    except Exception:
        print("Nodes:", list(app.get_graph().nodes.keys()))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="agentic_logistics", description="Autonomous carrier rerouting agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo_parser = subparsers.add_parser("demo", help="Run one scenario and print its trajectory")
    demo_parser.add_argument("--scenario", default="scenario_01_port_congestion.json")
    demo_parser.add_argument("--provider", default="mock", choices=["mock", "mock_flaky"])
    demo_parser.set_defaults(func=cmd_demo)

    eval_parser = subparsers.add_parser("eval", help="Run the full evaluation harness")
    eval_parser.set_defaults(func=cmd_eval)

    graph_parser = subparsers.add_parser("graph", help="Print the compiled graph structure")
    graph_parser.set_defaults(func=cmd_graph)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
