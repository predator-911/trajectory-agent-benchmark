"""Audit node: always runs on the success path.

Writes an immutable decision record (chosen route, rejected alternatives,
risk score, tool-call count) into the final state and, if configured,
appends it to a JSON-lines audit log file under reports/audit_logs/.
"""
from __future__ import annotations

import os
from typing import Callable

from agentic_logistics.config.settings import SYNTHETIC_LATENCY_MS
from agentic_logistics.domain.models import AuditRecord, RouteCandidate
from agentic_logistics.evaluation.trajectory import Step
from agentic_logistics.graph.nodes.deps import NodeDeps


def make_audit_node(deps: NodeDeps) -> Callable[[dict], dict]:
    def node(state: dict) -> dict:
        alert = state["alert"]
        risk_assessment = state.get("risk_assessment") or {}
        route = state.get("candidate_route")
        rejected = state.get("rejected_alternatives", [])

        trajectory = state["trajectory"]
        record = AuditRecord(
            alert_id=alert.alert_id,
            final_status="SUCCESS",
            chosen_route=RouteCandidate(**route) if route else None,
            rejected_alternatives=[RouteCandidate(**r) for r in rejected],
            risk_score=risk_assessment.get("risk_score"),
            escalation_reason=None,
            tool_call_count=trajectory.total_tool_calls(),
        )

        if deps.settings.get("write_audit_log_file", True):
            path = deps.settings.get("audit_log_path", "reports/audit_logs/audit_log.jsonl")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(record.model_dump_json() + "\n")

        step = Step(
            step_index=len(trajectory.steps),
            node_name="audit",
            reasoning_trace="Wrote immutable audit record for successful reroute.",
            latency_ms=SYNTHETIC_LATENCY_MS.get("audit", 60),
        )
        trajectory.add_step(step)
        trajectory.final_status = "SUCCESS"

        return {
            "trajectory": trajectory,
            "final_status": "SUCCESS",
        }

    return node
