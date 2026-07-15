"""Carrier lookup tool: pure function, deterministic, fixture-backed."""
from __future__ import annotations

from agentic_logistics.domain.errors import NoViableCarrierError
from agentic_logistics.domain.models import Carrier
from agentic_logistics.ports.carrier_repository import CarrierRepository


def carrier_lookup(
    repository: CarrierRepository,
    origin_region: str,
    destination_region: str,
    exclude_carrier_id: str | None = None,
) -> list[Carrier]:
    """Return viable carriers for a lane, excluding a known-affected carrier.

    Raises NoViableCarrierError if nothing matches -- callers decide whether
    that is retryable (transient lookup miss) or terminal (genuinely no lane
    coverage), based on how many attempts have already been made.
    """
    candidates = repository.find_by_region(origin_region, destination_region)
    candidates = [c for c in candidates if c.carrier_id != exclude_carrier_id and not c.blocklisted]
    if not candidates:
        raise NoViableCarrierError(
            f"No viable carriers for lane {origin_region} -> {destination_region}"
        )
    return candidates
