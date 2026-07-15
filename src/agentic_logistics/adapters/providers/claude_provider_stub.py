"""Stub adapter for Anthropic Claude. NOT wired into the default runtime path.

This class exists to prove the ports-and-adapters seam works: to go live,
implement the two methods below and register "claude" in
graph/build_graph.py's provider factory. Nothing else in the codebase changes.

A real implementation would:
  1. Accept a Claude API client (e.g. `anthropic.Anthropic()`) injected at
     construction time.
  2. In `plan()`, send the alert (serialized) plus a system prompt describing
     the fixed pipeline nodes, and ask Claude to return a structured plan
     (e.g. via tool-use / structured output) matching `PlanResult`'s schema.
  3. In `decide_tool_call()`, expose the tool registry's schemas to Claude as
     tool definitions and let Claude's native tool-calling select a tool name
     and arguments, mapped into `ToolCallDecision`.
  4. Read any credential from an environment variable such as
     ANTHROPIC_API_KEY -- this repository intentionally does NOT read that
     variable anywhere; wiring it in is left to a real deployment, not to
     this assignment submission.
"""
from __future__ import annotations

from typing import Any

from agentic_logistics.domain.models import TelemetryAlert
from agentic_logistics.ports.model_provider import ModelProvider, PlanResult, ToolCallDecision


class ClaudeProviderStub(ModelProvider):
    """Not implemented. See module docstring for the real wiring plan."""

    name = "claude"

    def plan(self, alert: TelemetryAlert) -> PlanResult:
        raise NotImplementedError(
            "ClaudeProviderStub.plan() is intentionally unimplemented in this "
            "submission (no paid API calls). See module docstring for the "
            "real integration plan."
        )

    def decide_tool_call(self, node_name: str, state: dict[str, Any]) -> ToolCallDecision:
        raise NotImplementedError(
            "ClaudeProviderStub.decide_tool_call() is intentionally unimplemented "
            "in this submission (no paid API calls). See module docstring for "
            "the real integration plan."
        )
