"""Trajectory data structures: the backbone of trajectory-based evaluation.

Every run produces a Trajectory: an ordered list of Steps. Metrics are
computed over the whole Trajectory, not just the final output -- this is
what makes the evaluation "trajectory-based" rather than outcome-only.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    expected_schema_valid: bool
    schema_valid: bool
    result: Optional[Any] = None
    error: Optional[str] = None


class Step(BaseModel):
    step_index: int
    node_name: str
    reasoning_trace: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    retry_of_step_index: Optional[int] = None
    latency_ms: int = 0
    token_cost_estimate: float = 0.0
    entities_referenced: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Trajectory(BaseModel):
    scenario_id: str
    provider_name: str
    steps: list[Step] = Field(default_factory=list)
    final_status: str = "IN_PROGRESS"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None

    def add_step(self, step: Step) -> None:
        self.steps.append(step)

    def total_latency_ms(self) -> int:
        return sum(s.latency_ms for s in self.steps)

    def total_tool_calls(self) -> int:
        return sum(len(s.tool_calls) for s in self.steps)

    def retry_steps(self) -> list[Step]:
        return [s for s in self.steps if s.retry_of_step_index is not None]
