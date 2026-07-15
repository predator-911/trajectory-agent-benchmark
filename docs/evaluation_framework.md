# Trajectory-Based Evaluation Framework

## Why trajectory-based, not outcome-only

Scoring only the final output of an agentic run hides exactly the failure modes that matter in production autonomy: a system that reaches the right answer via a hallucinated tool call, or that "succeeds" by silently skipping validation, looks identical to a healthy run if you only check the end state. This harness scores the **entire trajectory** — every node, every tool call, every retry — not just where it ended up.

## The Trajectory / Step / ToolCall schema

Every run of the pipeline (`graph/build_graph.py::run()`) produces a `Trajectory` (see `evaluation/trajectory.py`):

```
Trajectory
├── scenario_id, provider_name, final_status
└── steps: [Step]

Step
├── step_index, node_name, reasoning_trace
├── tool_calls: [ToolCall]
├── retry_of_step_index   (links a retry back to its origin step)
├── latency_ms, token_cost_estimate
└── entities_referenced   (carrier/route ids mentioned — used for hallucination detection)

ToolCall
├── tool_name, arguments
├── schema_valid          (checked at the ToolRegistry boundary, before execution)
└── result / error
```

## The ten evaluation dimensions

| Dimension | Metric function | What it measures |
|---|---|---|
| Planning | `plan_coherence` | Fraction of actual executed-node positions matching the scenario's expected canonical order |
| Tool selection | `tool_selection_precision` | Fraction of tool calls made that were the scenario's expected tool |
| Tool correctness | `schema_validity_rate` | Fraction of tool calls whose arguments passed the registry's schema check |
| State transitions | `valid_transition_rate` | Fraction of consecutive node-to-node transitions that are legal per the state diagram |
| Error recovery | `error_recovery_success_rate` | Of steps whose tool call errored, fraction followed by a successful retry of the same node |
| Retry count | `average_retries` | Count of steps flagged as a retry of an earlier step |
| Hallucination | `hallucination_rate` | Fraction of referenced entity ids (carrier/route ids) not present in the scenario's fixture ground truth |
| Task completion | `task_completion` | 1.0 if the trajectory's final status matches the scenario's expected terminal status, else 0.0 |
| Latency | `total_latency_ms` | Sum of each step's synthetic latency (deterministic per-node lookup table, illustrative only) |
| Cost | `estimated_cost` | Sum of each step's `token_cost_estimate` (0 for mock providers; a real adapter would populate this from actual token usage) |

All ten are implemented as pure functions in `evaluation/metrics.py`, each taking a `Trajectory` (+ the scenario's `ground_truth` dict where needed).

## Scoring rubric (0-4 per dimension)

| Score | Meaning |
|---|---|
| 4 — Excellent | Metric in the top of its expected range; zero unnecessary steps |
| 3 — Good | Minor inefficiency (one avoidable retry) but a fully correct outcome |
| 2 — Acceptable | Correct outcome via a degraded path (escalated when self-healing was possible, or hit the retry ceiling) |
| 1 — Poor | Wrong tool/entity used at least once; hallucinated a non-existent carrier/route |
| 0 — Failing | Task failed, an illegal state transition was taken, or a hallucination directly caused an incorrect execution action |

In this implementation, continuous [0,1] metrics are linearly scaled to [0,4] (`scorer._to_rubric`); this is a defensible, simple default — a richer implementation could bucket into discrete rubric bands with hand-tuned thresholds per dimension.

## Composite score

Weights are front-loaded toward safety-relevant dimensions, since the target use case is **autonomous execution** — a system that completes tasks reliably and recovers from errors safely matters more here than one that plans elegantly but occasionally acts on bad data:

```
composite = 0.25 * task_completion
          + 0.25 * error_recovery
          + 0.18 * tool_correctness
          + 0.18 * state_transitions
          + 0.07 * hallucination (inverted: 1 - rate)
          + 0.07 * planning
```

Latency and cost are reported in full on every `ScoreCard` but excluded from the composite: in this offline-mock context both are near-zero/illustrative for every provider, so folding them into the headline number would dilute it with noise rather than signal. A real deployment comparing an expensive frontier model against a cheap self-hosted one would want to re-weight this — that tradeoff is exactly the kind of judgment call surfaced in `docs/research_report.md` and the product-strategy deck.

## Honesty about what's actually measured here

Every number in this repo's shipped eval report comes from **`mock` and `mock_flaky`** — deterministic, rule-based providers, not real Claude or Qwen2.5 API calls (per the assignment's no-paid-API constraint). The harness itself, `evaluation/run_eval.py`, is provider-agnostic and would produce the same kind of report unchanged if pointed at a real `claude` or `ollama` adapter — see `docs/architecture.md`'s "Swapping in a real provider later" section.
