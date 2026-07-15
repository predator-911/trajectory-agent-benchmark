"""Stub adapter for an OpenAI GPT model. NOT wired into the default runtime path.

A real implementation would:
  1. Accept an OpenAI client injected at construction time.
  2. In `plan()`, use the Chat Completions or Responses API with a JSON-mode
     / structured-output request matching `PlanResult`'s schema.
  3. In `decide_tool_call()`, expose the tool registry's schemas as OpenAI
     function-calling tool definitions and map the model's function-call
     response into `ToolCallDecision`.
  4. Read any credential from an environment variable such as
     OPENAI_API_KEY -- this repository intentionally does NOT read that
     variable anywhere.
"""
from __future__ import annotations

from typing import Any

from agentic_logistics.domain.models import TelemetryAlert
from agentic_logistics.ports.model_provider import ModelProvider, PlanResult, ToolCallDecision


class OpenAIProviderStub(ModelProvider):
    """Not implemented. See module docstring for the real wiring plan."""

    name = "openai"

    def plan(self, alert: TelemetryAlert) -> PlanResult:
        raise NotImplementedError(
            "OpenAIProviderStub.plan() is intentionally unimplemented in this "
            "submission (no paid API calls)."
        )

    def decide_tool_call(self, node_name: str, state: dict[str, Any]) -> ToolCallDecision:
        raise NotImplementedError(
            "OpenAIProviderStub.decide_tool_call() is intentionally unimplemented "
            "in this submission (no paid API calls)."
        )
