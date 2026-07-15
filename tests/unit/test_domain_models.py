"""Unit tests for domain models: validation rules on core dataclasses."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentic_logistics.domain.models import Carrier, RouteCandidate, TelemetryAlert


def test_telemetry_alert_requires_regions():
    with pytest.raises(ValidationError):
        TelemetryAlert(alert_id="A1")  # missing origin_region/destination_region


def test_telemetry_alert_severity_optional():
    alert = TelemetryAlert(alert_id="A1", origin_region="X", destination_region="Y")
    assert alert.severity is None
    assert alert.alert_type == "unknown"


def test_carrier_reliability_score_bounds():
    with pytest.raises(ValidationError):
        Carrier(
            carrier_id="C1",
            name="Test",
            regions_served=["X"],
            cost_per_mile=1.0,
            avg_transit_hours=10.0,
            reliability_score=1.5,  # out of [0,1] bounds
        )


def test_route_candidate_valid_construction():
    route = RouteCandidate(
        carrier_id="C1",
        origin_region="X",
        destination_region="Y",
        estimated_cost=100.0,
        estimated_transit_hours=24.0,
    )
    assert route.carrier_id == "C1"
    assert route.estimated_cost == 100.0
