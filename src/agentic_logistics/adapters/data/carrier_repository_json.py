"""JSON-fixture-backed CarrierRepository adapter.

Deliberately dumb: no caching, no DB, just a fixture reader. This is a test
double for a real carrier-network service, not a production data layer.
"""
from __future__ import annotations

import json
from pathlib import Path

from agentic_logistics.domain.models import Carrier
from agentic_logistics.ports.carrier_repository import CarrierRepository

_DEFAULT_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "mock_carriers.json"


class JsonCarrierRepository(CarrierRepository):
    """Loads carriers from a JSON fixture file into memory."""

    def __init__(self, fixture_path: Path | str = _DEFAULT_FIXTURE_PATH) -> None:
        with open(fixture_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self._carriers: list[Carrier] = [Carrier(**item) for item in raw]

    def find_by_region(self, origin_region: str, destination_region: str) -> list[Carrier]:
        return [
            c
            for c in self._carriers
            if origin_region in c.regions_served and destination_region in c.regions_served
        ]

    def get(self, carrier_id: str) -> Carrier | None:
        for c in self._carriers:
            if c.carrier_id == carrier_id:
                return c
        return None

    def all_ids(self) -> list[str]:
        """Return every known carrier id -- used by hallucination-detection metrics."""
        return [c.carrier_id for c in self._carriers]
