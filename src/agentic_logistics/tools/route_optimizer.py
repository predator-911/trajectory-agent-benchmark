"""Route optimizer tool: picks the lowest-cost feasible route."""
from __future__ import annotations

from agentic_logistics.domain.errors import RouteInfeasibleError
from agentic_logistics.domain.models import Carrier, RouteCandidate


def route_optimizer(
    carriers: list[Carrier],
    origin_region: str,
    destination_region: str,
    max_transit_hours: float,
) -> tuple[RouteCandidate, list[RouteCandidate]]:
    """Return (chosen_route, rejected_alternatives).

    Chooses the lowest estimated_cost candidate among carriers whose
    avg_transit_hours is within max_transit_hours. Raises RouteInfeasibleError
    if none qualify.
    """
    feasible = [c for c in carriers if c.avg_transit_hours <= max_transit_hours]
    if not feasible:
        raise RouteInfeasibleError(
            f"No carrier meets max_transit_hours={max_transit_hours} for "
            f"{origin_region} -> {destination_region}"
        )
    feasible_sorted = sorted(feasible, key=lambda c: c.cost_per_mile)
    chosen_carrier = feasible_sorted[0]
    alternatives = feasible_sorted[1:]

    def to_route(c: Carrier) -> RouteCandidate:
        # Distance is not modeled explicitly in the mock fixtures; cost is
        # derived directly from cost_per_mile as a flat per-lane multiplier
        # (kept deliberately simple -- this is a deterministic simulation,
        # not a real routing engine).
        return RouteCandidate(
            carrier_id=c.carrier_id,
            origin_region=origin_region,
            destination_region=destination_region,
            estimated_cost=round(c.cost_per_mile * 500, 2),
            estimated_transit_hours=c.avg_transit_hours,
        )

    chosen = to_route(chosen_carrier)
    rejected = [to_route(c) for c in alternatives]
    return chosen, rejected
