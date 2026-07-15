"""Risk scoring tool: deterministic weighted heuristic over alert fields."""
from __future__ import annotations

from agentic_logistics.domain.models import RiskAssessment, Severity

_SEVERITY_WEIGHTS: dict[str, float] = {
    "low": 0.15,
    "medium": 0.4,
    "high": 0.7,
    "critical": 0.95,
}

_ALERT_TYPE_WEIGHTS: dict[str, float] = {
    "port_congestion": 0.1,
    "carrier_failure": 0.2,
    "weather_delay": 0.05,
    "customs_hold": 0.15,
    "unknown": 0.25,
}


def risk_scorer(
    alert_type: str,
    severity: Severity | None,
    affected_carrier_reliability: float | None,
) -> RiskAssessment:
    """Compute a deterministic risk score in [0, 1] from alert fields.

    If severity is missing (ambiguous alert), falls back to "medium" and
    records that fact in contributing_factors rather than fabricating a
    specific severity value.
    """
    factors: list[str] = []
    used_default = severity is None
    effective_severity = severity or "medium"
    if used_default:
        factors.append("severity missing on alert; defaulted to 'medium'")

    severity_component = _SEVERITY_WEIGHTS[effective_severity]
    type_component = _ALERT_TYPE_WEIGHTS.get(alert_type, _ALERT_TYPE_WEIGHTS["unknown"])
    factors.append(f"severity={effective_severity} contributes {severity_component:.2f}")
    factors.append(f"alert_type={alert_type} contributes {type_component:.2f}")

    reliability_component = 0.0
    if affected_carrier_reliability is not None:
        reliability_component = round((1.0 - affected_carrier_reliability) * 0.3, 3)
        factors.append(
            f"affected carrier reliability={affected_carrier_reliability:.2f} "
            f"contributes {reliability_component:.2f}"
        )

    raw_score = severity_component * 0.6 + type_component * 0.25 + reliability_component
    score = max(0.0, min(1.0, round(raw_score, 3)))

    rationale = (
        f"Computed from severity ({effective_severity}), alert_type ({alert_type}), "
        f"and affected-carrier reliability."
    )
    return RiskAssessment(risk_score=score, rationale=rationale, contributing_factors=factors)
