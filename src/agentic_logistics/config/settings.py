"""Plain-Python configuration. No secrets, no `.env` parsing, no os.environ reads.

Provider selection is a plain string/enum passed explicitly (CLI flag or a
constant here), never sourced from an environment variable.
"""
from __future__ import annotations

from dataclasses import dataclass

AVAILABLE_PROVIDERS = ("mock", "mock_flaky", "claude", "openai", "ollama")
DEFAULT_PROVIDER = "mock"


@dataclass(frozen=True)
class Settings:
    """Runtime-tunable pipeline parameters. All defaults, no secrets."""

    risk_escalation_threshold: float = 0.75
    max_transit_hours: float = 72.0
    max_retries_carrier_lookup: int = 2
    max_retries_route_optimizer: int = 2
    max_retries_execution: int = 1
    write_audit_log_file: bool = True
    audit_log_path: str = "reports/audit_logs/audit_log.jsonl"


DEFAULT_SETTINGS = Settings()


# Fixed synthetic per-node latency lookup table (milliseconds). Not sampled
# from a distribution -- a flat, deterministic value per node, used only for
# the illustrative "latency" evaluation dimension. Lives in config/ (not
# adapters/providers/) because graph/nodes/* need it and must never import
# from a concrete provider adapter -- see tests/regression/test_architecture_boundaries.py.
SYNTHETIC_LATENCY_MS: dict[str, int] = {
    "planner": 120,
    "risk": 90,
    "carrier_lookup": 150,
    "route_optimizer": 180,
    "validator": 80,
    "execution": 200,
    "audit": 60,
}
