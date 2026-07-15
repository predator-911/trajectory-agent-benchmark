"""Pure domain models. Zero I/O, zero framework dependencies.

Every other layer (tools, graph, evaluation) speaks in this vocabulary.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

AlertType = Literal[
    "port_congestion",
    "carrier_failure",
    "weather_delay",
    "customs_hold",
    "unknown",
]

Severity = Literal["low", "medium", "high", "critical"]

TerminalStatus = Literal["SUCCESS", "ESCALATED", "FAILED", "IN_PROGRESS"]


class TelemetryAlert(BaseModel):
    """A single disruption alert ingested from the telemetry feed."""

    alert_id: str
    alert_type: AlertType = "unknown"
    severity: Optional[Severity] = None
    origin_region: str
    destination_region: str
    affected_carrier_id: Optional[str] = None
    reported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = ""
    # Free-form bag for scenario-specific test hooks (error injection flags,
    # ground-truth-adjacent hints). Never used for business logic decisions,
    # only for deterministic test scaffolding read by mock providers.
    extra: dict = Field(default_factory=dict)


class Carrier(BaseModel):
    """A carrier available in the mock carrier network."""

    carrier_id: str
    name: str
    regions_served: list[str]
    cost_per_mile: float
    avg_transit_hours: float
    reliability_score: float = Field(ge=0.0, le=1.0)
    blocklisted: bool = False


class RouteCandidate(BaseModel):
    """A concrete proposed reroute using a specific carrier."""

    carrier_id: str
    origin_region: str
    destination_region: str
    estimated_cost: float
    estimated_transit_hours: float


class RiskAssessment(BaseModel):
    """Output of the risk-scoring step."""

    risk_score: float = Field(ge=0.0, le=1.0)
    rationale: str
    contributing_factors: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Output of the validator step."""

    is_valid: bool
    reasons: list[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    """Output of the (simulated) execution step."""

    executed: bool
    confirmation_id: Optional[str] = None
    error_message: Optional[str] = None


class AuditRecord(BaseModel):
    """Immutable record written once a trajectory reaches a terminal state."""

    alert_id: str
    final_status: TerminalStatus
    chosen_route: Optional[RouteCandidate] = None
    rejected_alternatives: list[RouteCandidate] = Field(default_factory=list)
    risk_score: Optional[float] = None
    escalation_reason: Optional[str] = None
    tool_call_count: int = 0
    written_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
