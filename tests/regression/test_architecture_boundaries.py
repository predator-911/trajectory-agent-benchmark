"""Regression test enforcing the Ports & Adapters import boundary described
in docs/architecture.md: code under graph/, evaluation/, and tools/ must
never import from adapters/providers/*. This is what keeps the "swap the
provider by changing one class" guarantee true over time.
"""
from __future__ import annotations

import re
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "agentic_logistics"
GUARDED_PACKAGES = ["graph", "evaluation", "tools"]
FORBIDDEN_IMPORT_PATTERN = re.compile(r"adapters\.providers")

# build_graph.py is the composition root: it is explicitly, deliberately the
# ONE place a concrete provider adapter is chosen (see its module docstring).
# Everything else under graph/ (nodes/, edges.py, state.py) must stay clean.
EXEMPT_FILES = {"build_graph.py"}


def test_guarded_packages_never_import_concrete_providers():
    violations = []
    for package in GUARDED_PACKAGES:
        package_dir = SRC_ROOT / package
        for path in package_dir.rglob("*.py"):
            if path.name in EXEMPT_FILES:
                continue
            text = path.read_text(encoding="utf-8")
            for line_no, line in enumerate(text.splitlines(), start=1):
                if FORBIDDEN_IMPORT_PATTERN.search(line) and not line.strip().startswith("#"):
                    violations.append(f"{path.relative_to(SRC_ROOT)}:{line_no}: {line.strip()}")

    assert not violations, (
        "Found forbidden imports of adapters.providers from a guarded package "
        "(graph/, evaluation/, tools/). These packages must depend only on "
        "ports/model_provider.py, never on a concrete provider adapter:\n"
        + "\n".join(violations)
    )
