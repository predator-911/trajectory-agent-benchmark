"""Domain-specific exceptions.

These exist so that graph conditional edges can branch on *exception type*
rather than on fragile string matching against error messages.
"""
from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain-level errors in agentic_logistics."""


class SchemaValidationError(DomainError):
    """Raised when a tool call's arguments do not match its declared JSON schema."""


class NoViableCarrierError(DomainError):
    """Raised when no carrier can be found matching the alert's lane/region."""


class RouteInfeasibleError(DomainError):
    """Raised when no candidate route satisfies business constraints."""


class ExecutionError(DomainError):
    """Raised when the (simulated) execution of a reroute fails.

    May be transient (retryable) or permanent (not retryable) — see the
    `transient` attribute.
    """

    def __init__(self, message: str, transient: bool = True) -> None:
        super().__init__(message)
        self.transient = transient
