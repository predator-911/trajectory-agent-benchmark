"""Stub adapter for a locally-hosted open model (e.g. Qwen2.5) via Ollama.

NOT wired into the default runtime path. A real implementation would:
  1. POST to a local Ollama HTTP endpoint, e.g. http://localhost:11434/api/generate
     or /api/chat, with model="qwen2.5:7b-instruct" (or similar).
  2. In `plan()`, prompt the local model to emit a structured plan and parse
     its JSON output into `PlanResult` (open models are typically noisier at
     structured output than Claude/GPT, so a real implementation would add a
     retry-with-repair loop here).
  3. In `decide_tool_call()`, prompt with the tool registry's schemas
     described in natural language (Ollama's function-calling support varies
     by model/version) and parse the resulting tool name + arguments into
     `ToolCallDecision`, validating against the registry before use.
  4. This adapter requires NO API key by design (local inference), which is
     part of why it does not need a secret-reading mechanism at all --
     only a local endpoint URL, which is a plain non-secret constant, not
     something requiring `.env` handling.
"""
from __future__ import annotations

from typing import Any

from agentic_logistics.domain.models import TelemetryAlert
from agentic_logistics.ports.model_provider import ModelProvider, PlanResult, ToolCallDecision


class OllamaProviderStub(ModelProvider):
    """Not implemented. See module docstring for the real wiring plan."""

    name = "ollama"

    def plan(self, alert: TelemetryAlert) -> PlanResult:
        raise NotImplementedError(
            "OllamaProviderStub.plan() is intentionally unimplemented in this "
            "submission. Intended to call a local Ollama endpoint -- see "
            "module docstring."
        )

    def decide_tool_call(self, node_name: str, state: dict[str, Any]) -> ToolCallDecision:
        raise NotImplementedError(
            "OllamaProviderStub.decide_tool_call() is intentionally unimplemented "
            "in this submission. Intended to call a local Ollama endpoint -- "
            "see module docstring."
        )
