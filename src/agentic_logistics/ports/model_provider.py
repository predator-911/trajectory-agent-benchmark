"""The single seam through which agent "cognition" is provided.

Everything under graph/, evaluation/, and tools/ depends ONLY on this
abstract interface -- never on a concrete adapter under adapters/providers/.
Swapping models later means writing one new class here and registering it
in graph/build_graph.py's factory. Nothing else changes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from agentic_logistics.domain.models import TelemetryAlert


class PlanResult(BaseModel):
    """The Planner node's output: an ordered plan plus rationale."""

    ordered_nodes: list[str]
    rationale: str
    used_default_fallback: bool = False


class ToolCallDecision(BaseModel):
    """A provider's decision about which tool to call and with what arguments."""

    tool_name: str
    arguments: dict[str, Any]
    rationale: str


class ModelProvider(ABC):
    """Abstract port for any "model" that can plan and decide tool calls.

    Concrete adapters (mock, or later: Claude / GPT / Ollama / Qwen) implement
    this interface. Nodes in graph/nodes/*.py call only these two methods.
    """

    name: str = "abstract"

    @abstractmethod
    def plan(self, alert: TelemetryAlert) -> PlanResult:
        """Produce the ordered list of pipeline nodes required for this alert."""
        raise NotImplementedError

    @abstractmethod
    def decide_tool_call(self, node_name: str, state: dict[str, Any]) -> ToolCallDecision:
        """Decide which tool to invoke (and with what arguments) for a given node."""
        raise NotImplementedError
