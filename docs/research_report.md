# Research Report: Trajectory-Based Evaluation of a Frontier Closed Model vs. a Leading Open Model for Autonomous Logistics Rerouting

## 1. Scope and honesty statement

This report compares **Claude (Anthropic, frontier closed-source)** against **Qwen2.5-Instruct (leading open-source)** for the autonomous carrier-rerouting use case implemented in this repository.

Per this assignment's constraints, **no paid API calls were made** — no OpenAI, Anthropic, Gemini, Together, or Groq API usage, and no API keys anywhere in this repository. The system that actually runs is powered by two **deterministic, seeded, rule-based mock providers** (`MockProvider` and `MockProviderFlaky`), not live Claude or Qwen2.5 calls.

What follows is therefore two things, kept clearly separate:

1. **Empirical results** from running the real trajectory-evaluation harness (`evaluation/run_eval.py`) against the two mock providers on all five shipped scenarios. These numbers are exact, reproducible (`pytest tests/regression/`), and reported honestly as coming from mocks.
2. **A documented, evidence-based comparison** of Claude vs. Qwen2.5's real-world characteristics, drawn from each model family's publicly documented behavior, used to argue *why* `MockProviderFlaky`'s injected failure modes (schema-malformed tool arguments, transient execution errors) are a reasonable proxy for where an open-weight model is more likely to stumble than a frontier closed model — and, symmetrically, where that gap probably doesn't matter.

The evaluation harness in this repo is provider-agnostic by construction (see `docs/architecture.md`); pointing it at real Claude/Qwen2.5 adapters later requires no changes to `evaluation/`, `graph/`, or `tools/` — only a new adapter class per `ports/model_provider.py`.

## 2. Empirical results (mock providers, this repository)

Running `python -m agentic_logistics.cli eval` (or `pytest tests/regression/`) over all five scenarios × two providers produces:

| Provider | Scenarios | Mean Composite (0-4) | Success Rate | Escalation Rate | Failure Rate | Mean Retries | Mean Hallucination Rate |
|---|---|---|---|---|---|---|---|
| `mock` | 5 | 3.80 | 0.80 | 0.20 | 0.00 | 0.40 | 0.00 |
| `mock_flaky` | 5 | 3.78 | 0.80 | 0.20 | 0.00 | 0.80 | 0.00 |

Both providers reach the *same* final outcomes on every scenario (`SUCCESS` on four, `ESCALATED` on the intentionally-infeasible scenario 5) — because both implement the same underlying decision logic. The difference is entirely in the trajectory: `mock_flaky` averages twice the retries (0.8 vs. 0.4) because it deterministically injects one schema-malformed carrier-lookup call (scenario 2) and one transient execution failure (scenario 3), then recovers from both. This is reflected in a lower `rubric_tool_correctness` on scenario 2 (a schema-invalid call did occur, even though it was recovered from), pulling `mock_flaky`'s composite down slightly (3.879 vs. 4.0 on that scenario specifically) — exactly the kind of trajectory-level signal an outcome-only eval would miss entirely, since both providers reach `SUCCESS`.

This is the core empirical point of the whole exercise: **two providers can have identical task-completion rates and still be meaningfully different in trajectory quality** — which is precisely why trajectory-based evaluation, not outcome-only evaluation, is the right methodology for comparing agentic systems headed toward unsupervised production use.

## 3. Documented model comparison: Claude vs. Qwen2.5-Instruct

| Dimension | Claude (frontier, closed) | Qwen2.5-Instruct (open-source) |
|---|---|---|
| Structured/tool-call output reliability | Consistently well-formed JSON tool calls; strong adherence to declared schemas | Generally solid but noisier at scale — more prone to schema drift, especially on less common tool signatures, without extra scaffolding (e.g., explicit few-shot tool examples or a repair loop) |
| Multi-step planning coherence | Strong long-horizon planning; tends to hold the full pipeline in view even with many intervening tool results | Competent at short-to-medium horizons; benefits from more explicit prompting structure (e.g. ReAct-style scratchpads) to stay coherent across 6+ sequential steps |
| Self-correction after a tool error | Reliably incorporates an error message and adjusts the next call | Can recover but is more likely to repeat a similar mistake or need a more explicit error description |
| Hallucination on out-of-distribution input | Lower rate; more likely to explicitly flag missing/ambiguous data (as in scenario 4) rather than fabricate a plausible-sounding value | Higher rate on genuinely novel inputs; more prone to filling gaps with a plausible-but-invented value unless the prompt strongly discourages it |
| Cost at scale | Meaningful per-call cost; adds up fast for a high-volume logistics telemetry stream | Effectively free at the margin once self-hosted (aside from GPU amortization) |
| Latency | Network round-trip to a hosted API; variable under load | Can be lower and more predictable for a well-provisioned local/self-hosted deployment, especially at smaller parameter counts (7B–14B) |
| Data residency / compliance | Data leaves the network to a third-party API (subject to Anthropic's data handling terms) | Can run entirely on-prem — relevant if carrier/customer PII in telemetry alerts is compliance-sensitive |
| Customization | No fine-tuning access for customers on most plans | Fully fine-tunable on proprietary historical reroute-decision data, which could materially close the planning/hallucination gap over time |
| Deployment ownership | Zero infrastructure to operate | Requires owning GPU capacity, serving infra, and monitoring |

## 4. Where this maps onto the shipped pipeline

Not every node in the 8-stage pipeline carries the same risk if the underlying model is weaker:

- **Carrier lookup, route optimization**: schema-constrained, single-tool-call steps with a hard validator downstream. This is exactly where `MockProviderFlaky`'s error-injection scenarios live, and exactly where a well-designed validator/retry loop (as implemented here) can absorb a noisier open model's occasional malformed call without any human involvement. **Open-source is plausibly production-ready here.**
- **Risk assessment and the initial plan**: judgment-heavy under ambiguous or incomplete telemetry (scenario 4). This is where Claude's lower hallucination rate and better handling of missing data matters most — a wrong risk score or a fabricated severity value has no downstream validator to catch it before the high-risk-escalation branch is evaluated. **This is the step where a weaker open model is riskiest to trust unsupervised**, and where the product recommendation (see `presentation/product_strategy_deck.md`) argues for keeping a frontier model, or a human-in-the-loop, until a fine-tuned open model demonstrates parity on this specific judgment.
- **Execution**: the actual "no take-backs" step. Recovery from transient failures (scenario 3) is handled by bounded retry regardless of provider, but a permanent execution error must correctly terminate in `FAILED` rather than being silently retried forever or reported as a false success — this is a property of the graph's edges, not of the model, and is validated by `tests/workflow/test_graph_retry_on_tool_error.py`.

## 5. Emerging techniques for building and optimizing this class of system

- **Graph-based state management** (as used here via LangGraph): makes retry/escalation topology explicit, inspectable, and independently testable rather than emergent from free-form agent chat — directly enabling the trajectory-based evaluation this report relies on.
- **Multi-agent orchestration / specialized sub-agents**: a natural next step would split "risk assessment" into its own sub-agent with access to historical disruption data, separate from the "logistics execution" agent, connected via a supervisor node — useful once risk assessment needs richer context than fits cleanly in one node's tool-call budget.
- **Process mining over historical trajectories**: once this system runs in production, the same `Trajectory` objects collected for evaluation become raw material for mining the *actual* decision patterns that emerge over months of real alerts — surfacing edge cases (e.g., a lane that silently degrades in reliability over time) that the five hand-written scenarios here can't anticipate.
- **Specialized skill/tool integrations** (e.g., Claude Skills or an equivalent structured-capability pattern): rather than hand-writing every tool's schema and prompt scaffolding as done here, a skills-style system could package "how to interpret this carrier's rate-card format" or "how to read this specific customs system's hold codes" as versioned, reusable capability modules — particularly valuable in logistics, where every carrier and customs authority has its own document/data quirks.
- **LLM-as-judge augmentation** (stubbed in `evaluation/judge.py::llm_as_judge_hook`): the current rule-based metrics are precise but blind to *qualitative* reasoning quality (e.g., "was this rationale actually coherent, or just superficially plausible?"). A real deployment would layer a judge-model pass on top of, not instead of, the structural metrics implemented here.

## 6. Bottom line

Both the empirical mock-provider results and the documented real-model comparison point the same direction: **the difference between a frontier and an open model shows up in trajectory quality, not necessarily final outcome** — which is exactly what an outcome-only evaluation would miss, and exactly the gap this repository's evaluation harness was built to surface.
