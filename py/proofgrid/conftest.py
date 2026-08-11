"""Pytest configuration for the ProofGrid package tests.

Why this file exists: `test_inspect_integration.py` imports `inspect_ai`, which is declared in
the optional `inspect` extra rather than in `dev`. Under a `.[dev]` install the bare import
raised ModuleNotFoundError at COLLECTION time, and pytest treats a collection error as fatal —
the run ended `Interrupted: 1 error during collection` and the other 18 tests in this package
never executed. One missing optional dependency was taking down the entire Python suite.

Skipping from inside the test module was the first fix and it does work, but it forces the
`inspect_ai` imports below a `pytest.importorskip` call, and the repository's two lint regimes
cannot both accept that: standalone `isort` (run by `.github/workflows/proofgrid.yml`) requires
two blank lines before the call, while `ruff`'s `I001` (run by pre-commit) removes the second.
Gating collection from here leaves the test module's imports untouched at the top of the file,
so both regimes are satisfied without either being reconfigured.

A skip is a weaker signal than a pass, so this is only half the fix. The
`inspect-evaluation` job in the workflow installs `.[dev,inspect]` and runs these tests for
real; without it, an ignored module would be a silent pass. Those tests are credential-free —
they evaluate against `mockllm/model` — so that job needs no secrets.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def pytest_ignore_collect(collection_path: Path, config) -> bool | None:
    """Skip the Inspect tests when the optional `inspect` extra is not installed.

    A hook rather than a module-level `collect_ignore` list, and nothing at module scope
    between the imports and this `def`, because of a lint conflict in this repository: `isort`
    (run by `.github/workflows/proofgrid.yml`) requires two blank lines between the import
    block and whatever follows, while `ruff`'s `I001` (run by pre-commit) treats a comment or
    assignment in that position as part of the import block and requires one. A function
    definition is the one shape both accept — `py/autoevals/conftest.py` has the same
    imports-then-def form and passes both — so the gate lives entirely in here.

    Returning None rather than False for other paths matters: None means "no opinion" and lets
    other hooks decide, while False would actively force collection of every other file.
    """
    if collection_path.name != "test_inspect_integration.py":
        return None
    return importlib.util.find_spec("inspect_ai") is None
