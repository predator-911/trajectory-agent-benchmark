"""Rule-based judge for semantic-ish checks that plain metrics can't capture
cleanly (e.g. whether a referenced entity is genuinely hallucinated vs. a
reasonable fixture-derived id). Includes a clearly-labeled, unimplemented
hook for a future LLM-as-judge upgrade -- following the same
"stub now, swap later" pattern as the provider adapters.
"""
from __future__ import annotations

from agentic_logistics.evaluation.trajectory import Trajectory


def rule_based_hallucination_check(trajectory: Trajectory, known_entity_ids: set[str]) -> list[str]:
    """Return the list of entity ids referenced in the trajectory that do not
    exist in the known entity universe (fixture carrier/route ids).
    """
    referenced = {e for s in trajectory.steps for e in s.entities_referenced if e}
    return sorted(referenced - known_entity_ids)


def llm_as_judge_hook(trajectory: Trajectory) -> None:
    """Not implemented in this submission (no paid API calls).

    A real upgrade would send the trajectory's reasoning traces to a strong
    judge model (e.g. Claude) with a rubric prompt and parse back a
    structured critique, used to augment (not replace) the rule-based
    metrics in metrics.py -- particularly useful for qualitatively judging
    `reasoning_trace` coherence, which purely structural metrics can't fully
    capture.
    """
    raise NotImplementedError(
        "llm_as_judge_hook is an intentionally unimplemented extension point. "
        "See docstring for the intended design."
    )
