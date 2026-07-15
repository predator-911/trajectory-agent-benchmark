"""Abstract interface for carrier data access.

Kept separate from ModelProvider because "data access" and "model inference"
are different concerns and should be independently mockable.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from agentic_logistics.domain.models import Carrier


class CarrierRepository(ABC):
    """Abstract port for looking up carriers."""

    @abstractmethod
    def find_by_region(self, origin_region: str, destination_region: str) -> list[Carrier]:
        """Return all carriers that service the given origin/destination regions."""
        raise NotImplementedError

    @abstractmethod
    def get(self, carrier_id: str) -> Carrier | None:
        """Return a single carrier by id, or None if it does not exist."""
        raise NotImplementedError
