"""Shared pytest fixtures and session-level guards (T-010).

Three fixtures — `repo_root`, `seeded_rng`, `tmp_repo` — and one session hook that
turns a zero-collected-items pytest run into a failure rather than a silent success.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pytest

from ambo.common.config import repo_root as _repo_root

# A fixed constant, never the global RNG state — determinism per the module-contract
# preamble (every test that needs randomness derives it from this one seed).
_SEEDED_RNG_SEED = 20260804


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """The repository root, discovered the same way `ambo.common.config.repo_root()`
    discovers it, so tests and runtime code agree on one definition."""
    return _repo_root()


@pytest.fixture
def seeded_rng() -> np.random.Generator:
    """A deterministic NumPy `Generator`, seeded from a fixed module-level constant."""
    return np.random.default_rng(_SEEDED_RNG_SEED)


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """A throwaway git repository inside `tmp_path`, with a local commit identity
    configured so commits succeed in CI. Reused by the layer-order tests in plan
    01-09."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test-runner@example.invalid"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=tmp_path, check=True)
    return tmp_path


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Fail loudly if the session collected zero test items.

    A mis-globbed `testpaths`, a renamed directory or an empty tree would otherwise
    let pytest exit 5 (`NO_TESTS_COLLECTED`) — which most CI wiring treats as neither
    pass nor fail, and `make test`'s own `$?` check would need to special-case it to
    catch it. Converting it into a hard failure here means `make test` cannot go green
    on nothing (the same silent-pass failure mode D-16 forbids in CI).
    """
    if exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED:
        collected = len(getattr(session, "items", []))
        print(
            f"\nFATAL: pytest collected {collected} test item(s) — a session that "
            "collects zero items must not report success (D-16)."
        )
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
