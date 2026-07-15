"""Workflow test: using mock_flaky, the graph actually takes a retry edge
and still reaches SUCCESS within the retry ceiling.
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


def test_carrier_lookup_retries_then_succeeds():
    alert = _load("scenario_02_carrier_failure.json")
    settings = replace(DEFAULT_SETTINGS, write_audit_log_file=False)
    trajectory = run(alert, provider_name="mock_flaky", settings=settings)

    assert trajectory.final_status == "SUCCESS"
    carrier_lookup_steps = [s for s in trajectory.steps if s.node_name == "carrier_lookup"]
    assert len(carrier_lookup_steps) == 2
    assert carrier_lookup_steps[0].tool_calls[0].error is not None
    assert carrier_lookup_steps[1].tool_calls[0].error is None
    assert carrier_lookup_steps[1].retry_of_step_index == carrier_lookup_steps[0].step_index


def test_execution_retries_after_transient_failure_then_succeeds():
    alert = _load("scenario_03_weather_delay.json")
    settings = replace(DEFAULT_SETTINGS, write_audit_log_file=False)
    trajectory = run(alert, provider_name="mock_flaky", settings=settings)

    assert trajectory.final_status == "SUCCESS"
    execution_steps = [s for s in trajectory.steps if s.node_name == "execution"]
    assert len(execution_steps) == 2
    assert execution_steps[0].tool_calls[0].error is not None
    assert execution_steps[1].tool_calls[0].error is None
