---
marp: true
title: Autonomous Carrier Rerouting — Product Strategy
paginate: true
---

# Autonomous Carrier Rerouting
### Trajectory-Based Evaluation → Product Strategy
15-minute walkthrough for technical and non-technical stakeholders

---

## The Problem

Logistics disruptions (port congestion, carrier failure, weather, customs holds) currently require a human to notice, evaluate alternatives, and manually rebook — costing hours per incident and scaling linearly with alert volume.

**Goal:** ingest a telemetry alert, evaluate alternatives, and execute a reroute autonomously — without waiting on a human, except when it's genuinely unsafe to proceed without one.

---

## Why This Is an Agentic Problem, Not a Simple Automation

A fixed if/then script breaks the moment a new disruption type or an unusual carrier combination appears. This needs a system that can:
- Plan a response to a *novel* alert shape
- Choose the right tool for each step
- Recover from a transient tool failure without giving up
- Know when to escalate instead of guessing

---

## Architecture in One Diagram

```
Telemetry Alert
      ↓
   Planner
      ↓
    Risk ──────────→ [High risk] → Escalate to human queue
      ↓
Carrier Lookup ──(retry on transient miss)──→ [Still none] → Escalate
      ↓
Route Optimizer ─────────────────────────────→ [Infeasible] → Escalate
      ↓
  Validator ──(send back to optimizer on invalid)
      ↓
  Execution ──(retry once on transient failure)──→ [Still fails] → FAILED (alert ops)
      ↓
   Audit (immutable decision record)
      ↓
   SUCCESS
```

Built on **LangGraph**: this pipeline *is* a directed graph over typed state — not a free-form agent chat — which is what makes every one of these branches independently testable.

---

## Evaluation Methodology: Trajectory, Not Just Outcome

Two systems can reach the *same* final answer via very different paths — one cleanly, one via a hallucinated tool call it got lucky with. Scoring only the final output can't tell them apart.

We score **every step**: planning, tool selection, tool correctness, state transitions, error recovery, retry count, hallucination, task completion, latency, cost.

---

## The Headline Result

| Provider | Mean Composite (0–4) | Success Rate | Mean Retries | Hallucination Rate |
|---|---|---|---|---|
| Baseline | 3.80 | 80% | 0.40 | 0.0% |
| Fault-injected | 3.78 | 80% | 0.80 | 0.0% |

**Same outcomes. Different trajectories.** The fault-injected run recovered from every injected error automatically — but that recovery cost measurable trajectory quality even though the final answer was identical. This is the signal outcome-only evaluation misses entirely.

---

## Claude vs. Qwen2.5: Where the Real Gap Is

| | Claude (frontier, closed) | Qwen2.5-Instruct (open) |
|---|---|---|
| Structured tool calls | Very reliable | Solid, noisier at scale |
| Planning coherence | Strong, long-horizon | Good, needs more scaffolding |
| Hallucination on ambiguous input | Lower | Higher |
| Cost / data residency | Per-call cost, third-party | Free at margin, on-prem possible |
| Fine-tunable on our data | No | Yes |

---

## Where Open-Source Is Ready Today

**Carrier Lookup & Route Optimization**: schema-constrained, single-tool-call steps with a hard validator immediately downstream. Our validator/retry loop absorbs a noisier model's occasional malformed call automatically — **recommend open-source here now.**

---

## Where We'd Keep the Frontier Model (For Now)

**Risk Assessment & Initial Planning**: judgment-heavy under ambiguous/incomplete telemetry, with *no validator downstream* to catch a bad call before the autonomous-execution decision is made. This is where hallucination cost is highest and hardest to detect.

**Recommendation: frontier model (or human-in-the-loop) here, until a fine-tuned open model demonstrates measured parity on this specific step.**

---

## Where We'd Never Go Fully Unsupervised

**Execution**: the one step with no take-backs. Regardless of model, this stays gated behind the Validator, with retry limits and a hard `FAILED` (not silent retry-forever) terminal state — a property of the *graph*, not of the model choice.

---

## Product Recommendation Summary

| Pipeline Stage | Recommendation |
|---|---|
| Carrier Lookup | Open-source, ready now |
| Route Optimization | Open-source, ready now |
| Risk Assessment | Frontier model, or human-in-loop |
| Planning (ambiguous alerts) | Frontier model |
| Execution | Model-agnostic — gated by validator + bounded retries either way |

**This is a per-stage decision, not a single yes/no for the whole system.**

---

## Roadmap

1. Wire a real Claude adapter for Risk/Planning; real Qwen2.5 (via Ollama) for Carrier Lookup/Route Optimization — no code changes needed outside `adapters/providers/`.
2. Add LLM-as-judge scoring on top of the structural metrics for qualitative reasoning-trace review.
3. Multi-agent split: dedicated risk sub-agent with access to historical disruption data.
4. Process-mining pass over production trajectories to discover edge cases beyond our five hand-written scenarios.
5. Fine-tune the open model on our historical reroute decisions to close the planning/hallucination gap.

---

## Risks & Open Questions

- Composite score weighting (front-loaded toward safety) is a defensible starting point, not a proven optimum — worth revisiting with real production incident data.
- All benchmark numbers here come from deterministic mock providers, calibrated to plausibly emulate documented model behavior — not live API calls. Real Claude/Qwen2.5 numbers are the next validation step.
- Escalation volume at scale needs a staffed human queue — this system reduces manual work, it doesn't eliminate the need for human judgment entirely.

---

# Questions?
