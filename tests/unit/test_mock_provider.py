"""Unit tests proving MockProvider is genuinely deterministic.

This determinism is required for the regression test tier to be meaningful:
the same scenario through the same provider must produce identical decisions.
"""
from __future__ import annotations

from agentic_logistics.adapters.providers.mock_provider import MockProvider
from agentic_logistics.adapters.providers.mock_provider_flaky import MockProviderFlaky
from agentic_logistics.domain.models import TelemetryAlert


def _alert() -> TelemetryAlert:
    return TelemetryAlert(
        alert_id="A1",
        alert_type="port_congestion",
        severity="high",
        origin_region="APAC-EAST",
        destination_region="US-WEST",
        affected_carrier_id="CARR-001",
    )


def test_plan_is_deterministic_across_calls():
    provider = MockProvider(seed=42)
    alert = _alert()
    plan1 = provider.plan(alert)
    plan2 = provider.plan(alert)
    assert plan1.ordered_nodes == plan2.ordered_nodes
    assert plan1.rationale == plan2.rationale
    assert plan1.used_default_fallback == plan2.used_default_fallback


def test_decide_tool_call_is_deterministic_across_calls():
    provider = MockProvider(seed=42)
    alert = _alert()
    state = {"alert": alert, "retry_counts": {}, "affected_carrier_reliability": 0.92}
    d1 = provider.decide_tool_call("risk", state)
    d2 = provider.decide_tool_call("risk", state)
    assert d1.tool_name == d2.tool_name
    assert d1.arguments == d2.arguments


def test_plan_flags_missing_severity_as_default_fallback():
    provider = MockProvider()
    alert = TelemetryAlert(alert_id="A2", origin_region="X", destination_region="Y")
    plan = provider.plan(alert)
    assert plan.used_default_fallback is True


def test_flaky_provider_falls_back_to_base_behavior_when_no_injection_configured():
    provider = MockProviderFlaky()
    alert = _alert()  # no inject_failures set
    state = {"alert": alert, "retry_counts": {}}
    decision = provider.decide_tool_call("carrier_lookup", state)
    assert "destination_region" in decision.arguments


def test_flaky_provider_injects_malformed_carrier_lookup_on_first_attempt_only():
    provider = MockProviderFlaky()
    alert = TelemetryAlert(
        alert_id="A3",
        origin_region="EU-WEST",
        destination_region="US-EAST",
        extra={"inject_failures": {"carrier_lookup": "malformed_then_ok"}},
    )
    first_attempt_state = {"alert": alert, "retry_counts": {}}
    first_decision = provider.decide_tool_call("carrier_lookup", first_attempt_state)
    assert "destination_region" not in first_decision.arguments

    retry_state = {"alert": alert, "retry_counts": {"carrier_lookup": 1}}
    retry_decision = provider.decide_tool_call("carrier_lookup", retry_state)
    assert "destination_region" in retry_decision.arguments
