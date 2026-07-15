"""Shared dependency bundle injected into every node.

Nodes are built as closures over a NodeDeps instance by graph/build_graph.py
(the composition root). This is the only place a concrete ModelProvider
adapter is instantiated and handed out.
"""
from __future__ import annotations

from dataclasses import dataclass

from agentic_logistics.ports.carrier_repository import CarrierRepository
from agentic_logistics.ports.model_provider import ModelProvider
from agentic_logistics.tools.registry import ToolRegistry


@dataclass
class NodeDeps:
    provider: ModelProvider
    tool_registry: ToolRegistry
    carrier_repository: CarrierRepository
    settings: dict
