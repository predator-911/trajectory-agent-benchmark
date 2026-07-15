"""Workflow test: a clean scenario runs Planner..Audit with SUCCESS and no retries."""
from __future__ import annotations

import json
from pathlib import Path

from agentic_logistics.config.settings import DEFAULT_SETTINGS
from agentic_logistics.domain.models import TelemetryAlert
from agentic_logistics.graph.build_graph import run

SCENARIOS_DIR = Path(__file__).resolve().parents[2] / "scenarios"


def _load(name: str) -> TelemetryAlert:
    with open(SCENARIOS_DIR / name, "r", encoding="utf-8") as f:
        scenario = json.load(f)
    return TelemetryAlert(**scenario["alert"])


def test_happy_path_reaches_success_with_expected_node_sequence():
    alert = _load("scenario_01_port_congestion.json")
    settings = _no_audit_write()
    trajectory = run(alert, provider_name="mock", settings=settings)

    assert trajectory.final_status == "SUCCESS"
    node_sequence = [s.node_name for s in trajectory.steps]
    assert node_sequence == [
        "planner",
        "risk",
        "carrier_lookup",
        "route_optimizer",
        "validator",
        "execution",
        "audit",
    ]
    assert trajectory.retry_steps() == []


def _no_audit_write():
    from dataclasses import replace

    return replace(DEFAULT_SETTINGS, write_audit_log_file=False)
