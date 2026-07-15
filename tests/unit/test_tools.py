"""Unit tests for individual tool functions."""
from __future__ import annotations

import pytest

from agentic_logistics.adapters.data.carrier_repository_json import JsonCarrierRepository
from agentic_logistics.domain.errors import NoViableCarrierError, RouteInfeasibleError
from agentic_logistics.domain.models import Carrier, RouteCandidate
from agentic_logistics.tools.carrier_lookup import carrier_lookup
from agentic_logistics.tools.execution_simulator import execution_simulator
from agentic_logistics.tools.risk_scorer import risk_scorer
from agentic_logistics.tools.route_optimizer import route_optimizer
from agentic_logistics.tools.route_validator import route_validator


@pytest.fixture()
def repo() -> JsonCarrierRepository:
    return JsonCarrierRepository()


def test_carrier_lookup_returns_matching_carriers(repo):
    carriers = carrier_lookup(repo, "APAC-EAST", "US-WEST")
    ids = {c.carrier_id for c in carriers}
    assert ids == {"CARR-001", "CARR-003"}


def test_carrier_lookup_excludes_affected_carrier(repo):
    carriers = carrier_lookup(repo, "APAC-EAST", "US-WEST", exclude_carrier_id="CARR-001")
    ids = {c.carrier_id for c in carriers}
    assert ids == {"CARR-003"}


def test_carrier_lookup_excludes_blocklisted(repo):
    with pytest.raises(NoViableCarrierError):
        carrier_lookup(repo, "EU-WEST", "EU-EAST")


def test_carrier_lookup_raises_on_no_match(repo):
    with pytest.raises(NoViableCarrierError):
        carrier_lookup(repo, "AFRICA-SOUTH", "ANTARCTICA-RESEARCH")


def test_route_optimizer_picks_lowest_cost():
    carriers = [
        Carrier(carrier_id="A", name="A", regions_served=["X", "Y"], cost_per_mile=2.0, avg_transit_hours=10, reliability_score=0.9),
        Carrier(carrier_id="B", name="B", regions_served=["X", "Y"], cost_per_mile=1.0, avg_transit_hours=10, reliability_score=0.9),
    ]
    chosen, rejected = route_optimizer(carriers, "X", "Y", max_transit_hours=72)
    assert chosen.carrier_id == "B"
    assert [r.carrier_id for r in rejected] == ["A"]


def test_route_optimizer_raises_when_no_carrier_meets_transit_constraint():
    carriers = [
        Carrier(carrier_id="A", name="A", regions_served=["X", "Y"], cost_per_mile=2.0, avg_transit_hours=100, reliability_score=0.9),
    ]
    with pytest.raises(RouteInfeasibleError):
        route_optimizer(carriers, "X", "Y", max_transit_hours=72)


def test_risk_scorer_defaults_missing_severity_without_fabricating():
    result = risk_scorer(alert_type="unknown", severity=None, affected_carrier_reliability=None)
    assert any("defaulted to 'medium'" in f for f in result.contributing_factors)
    assert 0.0 <= result.risk_score <= 1.0


def test_risk_scorer_is_deterministic():
    r1 = risk_scorer(alert_type="carrier_failure", severity="high", affected_carrier_reliability=0.5)
    r2 = risk_scorer(alert_type="carrier_failure", severity="high", affected_carrier_reliability=0.5)
    assert r1.risk_score == r2.risk_score


def test_route_validator_flags_transit_violation():
    route = RouteCandidate(carrier_id="A", origin_region="X", destination_region="Y", estimated_cost=100, estimated_transit_hours=100)
    result = route_validator(route, max_transit_hours=72)
    assert result.is_valid is False
    assert result.reasons


def test_route_validator_passes_valid_route():
    route = RouteCandidate(carrier_id="A", origin_region="X", destination_region="Y", estimated_cost=100, estimated_transit_hours=24)
    result = route_validator(route, max_transit_hours=72)
    assert result.is_valid is True


def test_execution_simulator_success():
    result = execution_simulator("CARR-001", "A1", force_transient_failure_then_succeed=False, attempt_number=1)
    assert result.executed is True
    assert result.confirmation_id is not None


def test_execution_simulator_transient_failure_then_success():
    from agentic_logistics.domain.errors import ExecutionError

    with pytest.raises(ExecutionError) as exc_info:
        execution_simulator("CARR-001", "A1", force_transient_failure_then_succeed=True, attempt_number=1)
    assert exc_info.value.transient is True

    result = execution_simulator("CARR-001", "A1", force_transient_failure_then_succeed=True, attempt_number=2)
    assert result.executed is True
