"""Shared helper used by every node to invoke a tool through the registry
and record the attempt as a trajectory ToolCall, regardless of outcome.
"""
from __future__ import annotations

from typing import Any

from agentic_logistics.domain.errors import DomainError
from agentic_logistics.evaluation.trajectory import ToolCall
from agentic_logistics.tools.registry import ToolRegistry


def invoke_and_record(
    tool_registry: ToolRegistry, tool_name: str, arguments: dict[str, Any]
) -> tuple[Any, ToolCall, Exception | None]:
    """Call a tool via the registry, returning (result, ToolCall, exception).

    If validation or execution fails, result is None and the exception is
    returned so the calling node can decide how to react (retry, escalate).
    The ToolCall record itself always reflects what actually happened -- it
    is never suppressed on failure, since evaluation needs the full history.
    """
    schema_valid = tool_registry.is_valid_schema(tool_name, arguments)
    try:
        result = tool_registry.call(tool_name, arguments)
        tool_call = ToolCall(
            tool_name=tool_name,
            arguments=arguments,
            expected_schema_valid=True,
            schema_valid=schema_valid,
            result=_safe_serialize(result),
            error=None,
        )
        return result, tool_call, None
    except DomainError as exc:
        tool_call = ToolCall(
            tool_name=tool_name,
            arguments=arguments,
            expected_schema_valid=True,
            schema_valid=schema_valid,
            result=None,
            error=str(exc),
        )
        return None, tool_call, exc


def _safe_serialize(result: Any) -> Any:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, tuple):
        return [
            item.model_dump() if hasattr(item, "model_dump") else item for item in result
        ]
    if isinstance(result, list):
        return [item.model_dump() if hasattr(item, "model_dump") else item for item in result]
    return result
