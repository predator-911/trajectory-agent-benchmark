"""Route validator tool: checks a proposed route against business rules."""
from __future__ import annotations

from agentic_logistics.domain.models import RouteCandidate, ValidationResult


def route_validator(route: RouteCandidate, max_transit_hours: float) -> ValidationResult:
    """Validate a proposed route.

    Rules:
      - estimated_transit_hours must not exceed max_transit_hours.
      - estimated_cost must be a positive number.
    """
    reasons: list[str] = []
    if route.estimated_transit_hours > max_transit_hours:
        reasons.append(
            f"estimated_transit_hours ({route.estimated_transit_hours}) exceeds "
            f"max_transit_hours ({max_transit_hours})"
        )
    if route.estimated_cost <= 0:
        reasons.append("estimated_cost must be positive")

    return ValidationResult(is_valid=len(reasons) == 0, reasons=reasons)
