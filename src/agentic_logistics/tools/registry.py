"""Tool registry: the only way nodes may invoke a tool.

Nodes never import a tool function directly. They ask the registry to run a
named tool with a dict of arguments. The registry validates arguments against
the tool's declared JSON-schema-like spec before calling it, and raises
SchemaValidationError if validation fails. This is what lets evaluation
metrics generically compute "schema validity rate" for ANY tool without
special-casing each one.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from agentic_logistics.domain.errors import SchemaValidationError


@dataclass
class ToolSpec:
    """A registered tool: its callable plus a minimal argument schema.

    `schema` maps argument name -> expected python type. This is intentionally
    a simple, dependency-free stand-in for a full JSON Schema validator --
    sufficient to detect the malformed-argument injection scenarios used in
    the evaluation harness.
    """

    name: str
    func: Callable[..., Any]
    schema: dict[str, type]
    required: set[str]


class ToolRegistry:
    """Central registry of all tools available to the agent graph."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, name: str, func: Callable[..., Any], schema: dict[str, type], required: set[str] | None = None) -> None:
        self._tools[name] = ToolSpec(name=name, func=func, schema=schema, required=required or set(schema.keys()))

    def validate_arguments(self, name: str, arguments: dict[str, Any]) -> None:
        spec = self._tools.get(name)
        if spec is None:
            raise SchemaValidationError(f"Unknown tool '{name}'")
        missing = spec.required - set(arguments.keys())
        if missing:
            raise SchemaValidationError(
                f"Tool '{name}' missing required arguments: {sorted(missing)}"
            )
        for key, value in arguments.items():
            expected_type = spec.schema.get(key)
            if expected_type is not None and not isinstance(value, expected_type):
                raise SchemaValidationError(
                    f"Tool '{name}' argument '{key}' expected {expected_type.__name__}, "
                    f"got {type(value).__name__}"
                )

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        """Validate arguments against the tool's schema, then invoke it.

        Raises SchemaValidationError before ever calling the underlying
        function if arguments are malformed -- this is intentional: schema
        validity is checked at the registry boundary, not inside each tool.
        """
        self.validate_arguments(name, arguments)
        spec = self._tools[name]
        return spec.func(**arguments)

    def is_valid_schema(self, name: str, arguments: dict[str, Any]) -> bool:
        try:
            self.validate_arguments(name, arguments)
            return True
        except SchemaValidationError:
            return False

    def names(self) -> list[str]:
        return list(self._tools.keys())
