"""dbt-invoking integration tests for the warehouse build (T-201, plan 03-01).

This file is extended by later plans in Phase 3:
  - plan 03-03 adds the poisoned-fixture proof (D-11): a duplicate-grain-key fixture
    pointed at via `--vars`, asserting `dbt build` fails on the `unique` test.
  - plan 03-04 adds the AD-042 reconciliation assertions (mart revenue vs the
    simulator's disclosed CSV totals, all three Layer P layers).
  - plan 03-06 adds the Layer R fixture run (D-20): a minimal fake
    `data/real_anon/`-shaped fixture built with `layer_r_present: true`.

`_run_dbt` is the shared subprocess helper every one of those additions reuses, so
the always-present dbt invocation prefix is defined exactly once.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ambo.common.config import load_settings

_DBT_BUILD_PREFIX: tuple[str, ...] = (
    "uv",
    "run",
    "dbt",
    "build",
    "--project-dir",
    "dbt",
    "--profiles-dir",
    "dbt",
)


def _run_dbt(
    repo_root: Path, *extra_args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run `uv run dbt build --project-dir dbt --profiles-dir dbt <extra_args>` from
    `repo_root`, never raising on a non-zero exit -- callers assert on `.returncode`
    themselves so a red run's stdout/stderr can be surfaced in the assertion message."""
    run_env = dict(os.environ) if env is None else env
    return subprocess.run(
        [*_DBT_BUILD_PREFIX, *extra_args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        env=run_env,
    )


def test_make_transform_builds_the_project(repo_root: Path) -> None:
    result = _run_dbt(repo_root)

    tail = "\n".join(result.stdout.splitlines()[-40:])
    assert result.returncode == 0, (
        "`uv run dbt build --project-dir dbt --profiles-dir dbt` exited "
        f"{result.returncode}, expected 0. Last 40 lines of stdout:\n{tail}"
    )


def test_warehouse_file_lands_at_settings_path(repo_root: Path) -> None:
    result = _run_dbt(repo_root)
    tail = "\n".join(result.stdout.splitlines()[-40:])
    assert result.returncode == 0, (
        f"dbt build failed before the warehouse-path assertion could run. Last 40 "
        f"lines of stdout:\n{tail}"
    )

    warehouse_path = load_settings().paths.warehouse
    assert warehouse_path.is_file(), (
        f"load_settings().paths.warehouse ({warehouse_path}) does not exist after a "
        "successful dbt build."
    )

    # The specific wrong-resolution outcome RESEARCH.md Pitfall 1 warns about: a
    # relative `path:` in profiles.yml resolving one directory above the repository
    # root instead of against the CWD at invocation. This test is the regression
    # guard for dbt-duckdb's CWD-relative path resolution and must be re-verified if
    # the dbt-core/dbt-duckdb pins in uv.lock ever change (RESEARCH.md Pitfall 1).
    wrong_location = repo_root.parent / "ambo.duckdb"
    assert not wrong_location.exists(), (
        f"A database file exists at {wrong_location}, one directory above the "
        "repository root -- this is the exact wrong-resolution outcome RESEARCH.md "
        "Pitfall 1 warns about; re-verify dbt/profiles.yml's dev.path has no `../` "
        "prefix and that the dbt-core/dbt-duckdb pins in uv.lock have not changed "
        "path-resolution behavior."
    )
