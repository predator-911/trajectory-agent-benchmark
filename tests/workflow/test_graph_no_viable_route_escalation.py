"""Workflow test: a scenario with no feasible carriers must terminate in
ESCALATED, never in a silent failure or a hallucinated success.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from agentic_logistics.config.settings import DEFAULT_SETTINGS
from agentic_logistics.domain.models import TelemetryAlert
from agentic_logistics.graph.build_graph import run

SCENARIOS_DIR = Path(__file__).resolve().parents[2] / "scenarios"


def _load(name: str) -> TelemetryAlert:
    with open(SCENARIOS_DIR / name, "r", encoding="utf-8") as f:
        scenario = json.load(f)
    return TelemetryAlert(**scenario["alert"])


def test_no_viable_route_escalates_after_retry_ceiling():
    alert = _load("scenario_05_no_viable_route.json")
    settings = replace(DEFAULT_SETTINGS, write_audit_log_file=False)
    trajectory = run(alert, provider_name="mock", settings=settings)

    assert trajectory.final_status == "ESCALATED"
    carrier_lookup_steps = [s for s in trajectory.steps if s.node_name == "carrier_lookup"]
    # max_retries_carrier_lookup=2 -> initial attempt + 2 retries = 3 attempts
    assert len(carrier_lookup_steps) == 3
    assert all(s.tool_calls[0].error is not None for s in carrier_lookup_steps)
    # Must never reach route_optimizer/execution on an infeasible lane.
    assert not any(s.node_name in ("route_optimizer", "execution", "audit") for s in trajectory.steps)
