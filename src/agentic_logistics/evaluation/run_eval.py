"""Runs every scenario under scenarios/*.json through the pipeline for each
configured provider, scores each resulting trajectory, and writes both a
machine-readable JSON report and a human-readable Markdown report to
reports/eval_results/.
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from agentic_logistics.config.settings import DEFAULT_SETTINGS
from agentic_logistics.domain.models import TelemetryAlert
from agentic_logistics.evaluation.scorer import ScoreCard, compute_scorecard
from agentic_logistics.graph.build_graph import run as run_pipeline

SCENARIOS_DIR = Path(__file__).resolve().parents[3] / "scenarios"
REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports" / "eval_results"

DEFAULT_PROVIDERS = ("mock", "mock_flaky")


def load_scenarios() -> list[dict]:
    scenarios = []
    for path in sorted(SCENARIOS_DIR.glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            scenarios.append(json.load(f))
    return scenarios


def run_all(providers: tuple[str, ...] = DEFAULT_PROVIDERS) -> list[ScoreCard]:
    scenarios = load_scenarios()
    scorecards: list[ScoreCard] = []
    # Evaluation runs never write to the shared audit log file to keep
    # eval reproducible and side-effect-free across repeated invocations.
    eval_settings = DEFAULT_SETTINGS.__class__(
        risk_escalation_threshold=DEFAULT_SETTINGS.risk_escalation_threshold,
        max_transit_hours=DEFAULT_SETTINGS.max_transit_hours,
        max_retries_carrier_lookup=DEFAULT_SETTINGS.max_retries_carrier_lookup,
        max_retries_route_optimizer=DEFAULT_SETTINGS.max_retries_route_optimizer,
        max_retries_execution=DEFAULT_SETTINGS.max_retries_execution,
        write_audit_log_file=False,
        audit_log_path=DEFAULT_SETTINGS.audit_log_path,
    )

    for scenario in scenarios:
        alert = TelemetryAlert(**scenario["alert"])
        ground_truth = scenario["ground_truth"]
        for provider_name in providers:
            trajectory = run_pipeline(alert, provider_name=provider_name, settings=eval_settings)
            scorecard = compute_scorecard(trajectory, ground_truth)
            scorecards.append(scorecard)
    return scorecards


def _aggregate_by_provider(scorecards: list[ScoreCard]) -> dict[str, dict]:
    by_provider: dict[str, list[ScoreCard]] = {}
    for sc in scorecards:
        by_provider.setdefault(sc.provider_name, []).append(sc)

    summary = {}
    for provider, cards in by_provider.items():
        composites = [c.composite_score for c in cards]
        latencies = sorted(c.total_latency_ms for c in cards)
        summary[provider] = {
            "num_scenarios": len(cards),
            "mean_composite_score": round(statistics.mean(composites), 3),
            "min_composite_score": min(composites),
            "max_composite_score": max(composites),
            "success_rate": round(
                sum(1 for c in cards if c.final_status == "SUCCESS") / len(cards), 3
            ),
            "escalation_rate": round(
                sum(1 for c in cards if c.final_status == "ESCALATED") / len(cards), 3
            ),
            "failure_rate": round(
                sum(1 for c in cards if c.final_status == "FAILED") / len(cards), 3
            ),
            "p50_latency_ms": latencies[len(latencies) // 2] if latencies else 0,
            "p95_latency_ms": latencies[int(len(latencies) * 0.95) - 1] if latencies else 0,
            "mean_retries": round(statistics.mean(c.average_retries for c in cards), 3),
            "mean_hallucination_rate": round(
                statistics.mean(c.hallucination_rate for c in cards), 3
            ),
        }
    return summary


def write_reports(scorecards: list[ScoreCard]) -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = REPORTS_DIR / f"eval_report_{timestamp}.json"
    md_path = REPORTS_DIR / f"eval_report_{timestamp}.md"

    summary = _aggregate_by_provider(scorecards)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": timestamp,
                "summary_by_provider": summary,
                "scorecards": [sc.model_dump() for sc in scorecards],
            },
            f,
            indent=2,
            default=str,
        )

    lines = ["# Evaluation Report", "", f"Generated at {timestamp}", "", "## Summary by Provider", ""]
    lines.append("| Provider | Scenarios | Mean Composite | Success Rate | Escalation Rate | Failure Rate | P50 Latency (ms) | Mean Retries | Mean Hallucination |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for provider, s in summary.items():
        lines.append(
            f"| {provider} | {s['num_scenarios']} | {s['mean_composite_score']} | "
            f"{s['success_rate']} | {s['escalation_rate']} | {s['failure_rate']} | "
            f"{s['p50_latency_ms']} | {s['mean_retries']} | {s['mean_hallucination_rate']} |"
        )

    lines += ["", "## Per-Scenario Scorecards", ""]
    lines.append("| Scenario | Provider | Final Status | Composite | Planning | Tool Correctness | State Transitions | Error Recovery | Hallucination |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for sc in scorecards:
        lines.append(
            f"| {sc.scenario_id} | {sc.provider_name} | {sc.final_status} | {sc.composite_score} | "
            f"{sc.rubric_planning} | {sc.rubric_tool_correctness} | {sc.rubric_state_transitions} | "
            f"{sc.rubric_error_recovery} | {sc.rubric_hallucination} |"
        )

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return json_path, md_path


def main() -> None:
    scorecards = run_all()
    json_path, md_path = write_reports(scorecards)
    summary = _aggregate_by_provider(scorecards)
    print("Evaluation complete.")
    for provider, s in summary.items():
        print(f"  [{provider}] mean_composite={s['mean_composite_score']} success_rate={s['success_rate']}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")


if __name__ == "__main__":
    main()
