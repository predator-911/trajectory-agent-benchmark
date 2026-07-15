# Decision Log: AI Tool Usage

This assignment's policy requires documenting how AI coding tools were used, what was accepted/rejected, and which architectural decisions were made by hand. Written honestly, in first person, as the engineer.

## What was designed by hand, before any code was generated

The full architectural specification — the Ports & Adapters folder structure, the LangGraph framework choice (vs. CrewAI/AutoGen/OpenAI Agents SDK/LlamaIndex Workflows), the Claude-vs-Qwen2.5 model pairing, the ten-dimension trajectory evaluation methodology and its 0-4 rubric and composite weighting, the exact 8-node business workflow state diagram (including which failures are retryable vs. terminal, and the three distinct terminal-failure states), and the module-by-module responsibility breakdown — was all worked out **before** any code generation, in a structured planning conversation. That specification is what an AI coding assistant (in this case, generation was done turn-by-turn rather than via a single Codex invocation, since the available Codex quota was exhausted) then implemented against.

## What the AI assistant generated

Given the pre-written specification, the assistant generated:
- Every Python module under `src/agentic_logistics/` (domain models, ports, adapters, tools, graph nodes/edges, evaluation harness, CLI).
- All five scenario JSON fixtures with hand-checked ground truth.
- The full test suite (unit, workflow, evaluation, regression tiers).
- All documentation, diagrams, the presentation deck outline, and this log itself.
- Packaging/config files (`pyproject.toml`, `requirements.txt`, `.replit`, `Makefile`, GitHub Actions CI).

## What was accepted as-is vs. corrected during generation

This repository was **built and verified interactively**, not generated blind: after each module was written, it was actually executed (`pytest`, direct pipeline runs against every scenario, `ruff check`) before moving on, and issues were fixed immediately rather than assumed away. Specific corrections made during this process:

1. **Architecture-boundary leak**: `SYNTHETIC_LATENCY_MS` (the per-node synthetic latency table) was initially defined inside `adapters/providers/mock_provider.py`, but `graph/nodes/*.py` needed to reference it for `Step.latency_ms` — which would have violated the "graph/ never imports adapters/providers/" rule this repo enforces via `tests/regression/test_architecture_boundaries.py`. Caught by that same test failing on first run. Fixed by moving the constant into `config/settings.py`, a neutral location both layers can depend on.
2. **Composition-root exemption**: the architecture-boundary test initially flagged `graph/build_graph.py` itself for importing every provider adapter — which is *correct and intentional*, since `build_graph.py` is explicitly the composition root where providers are chosen. Fixed by exempting that one file by name in the test, with a comment explaining why, rather than weakening the rule for everyone else.
3. **Test logic bug**: an early unit test (`test_carrier_lookup_excludes_blocklisted`) asserted that looking up a lane served only by a blocklisted carrier would return an empty list — but `carrier_lookup`'s actual (and correct) contract is to raise `NoViableCarrierError` when nothing qualifies. Fixed the test to match the intended contract rather than loosening the contract to match a wrong test.
4. **Deprecation warnings**: `datetime.utcnow()` is deprecated in current Python; every usage was swapped to `datetime.now(timezone.utc)` after the warning surfaced during a real eval run.
5. **Scenario ground truth was verified empirically, not assumed**: rather than writing `expected_entities` / `expected_terminal_status` by hand-reasoning alone, each scenario was actually run through the pipeline first, the real trajectory inspected, and the ground truth written to match observed (and manually sanity-checked) correct behavior — then locked in as regression baselines.

## What was deliberately left as a stub, and why

The `ClaudeProviderStub`, `OpenAIProviderStub`, and `OllamaProviderStub` classes intentionally raise `NotImplementedError`. Given the "no paid APIs, no keys, no `.env`" constraint, wiring in a real API call would have meant either violating that constraint or writing untested, unverifiable dead code. Instead, each stub's docstring documents exactly what a real implementation would do — the honest, verifiable choice given the constraints, rather than pretending real integration work happened when it didn't.

## What a reviewer should scrutinize hardest

The composite-score weighting in `evaluation/scorer.py` (0.25/0.25/0.18/0.18/0.07/0.07) is a defensible starting point, not a rigorously derived optimum — it was chosen to front-load safety-relevant dimensions (task completion, error recovery) for an autonomous-execution use case, but reasonable people could weight this differently, and that tradeoff is called out explicitly in `docs/evaluation_framework.md` rather than presented as more authoritative than it is.
