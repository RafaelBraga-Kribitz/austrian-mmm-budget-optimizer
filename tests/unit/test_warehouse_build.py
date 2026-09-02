"""dbt-invoking integration tests for the warehouse build (T-201, plan 03-01).

This file is extended by later plans in Phase 3:
  - plan 03-03 adds the poisoned-fixture proof (D-11): a duplicate-grain-key fixture
    pointed at via `--vars`, asserting `dbt build` fails on the `unique` test.
  - plan 03-04 adds the AD-042 reconciliation assertions (mart revenue vs the
    simulator's disclosed CSV totals, all three Layer P layers) and the AD-040
    spine ordering assertions (gapless, ascending, uniform seven-day step).
  - plan 03-06 adds the Layer R fixture run (D-20): a minimal fake
    `data/real_anon/`-shaped fixture built with `layer_r_present: true`.

`_run_dbt` is the shared subprocess helper every one of those additions reuses, so
the always-present dbt invocation prefix is defined exactly once.
"""

from __future__ import annotations

import datetime
import itertools
import json
import os
import shutil
import subprocess
from pathlib import Path

import duckdb
import pytest

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


# --- Poisoned-fixture harness (D-11, T-03-08..T-03-11, plan 03-03) -------------------
#
# Proves a duplicate grain key FAILS `dbt build` by making it happen, rather than
# asserting a `unique` test merely exists (RESEARCH.md Pitfall 4). Reused as-is by
# plan 03-06's Layer R fixture run and Phase 6's intake tests -- the fixture, env
# helper and runner below are the one authored home for this pattern.


@pytest.fixture
def synthetic_tree_copy(repo_root: Path, tmp_path: Path) -> Path:
    """A throwaway copy of `data/synthetic/` inside `tmp_path`.

    Constructed at test time with `shutil.copytree` rather than committed under
    `tests/fixtures/` -- a duplicate copy of the nine synthetic artifacts would be a
    near-megabyte of near-identical data for a fixture this test suite only needs to
    corrupt by one line (D-11, Claude's Discretion)."""
    destination = tmp_path / "synthetic"
    shutil.copytree(repo_root / "data" / "synthetic", destination)
    return destination


def _dbt_env(tmp_path: Path) -> dict[str, str]:
    """A copy of the process environment with `AMBO_TEST_WAREHOUSE` and
    `DBT_TARGET_PATH` pointed inside `tmp_path`.

    A fixture build must never touch the real `data/warehouse/ambo.duckdb` (the
    `dev` target) and must never race the real `dbt/target/` directory another
    concurrent invocation may be writing to (T-03-10)."""
    env = dict(os.environ)
    env["AMBO_TEST_WAREHOUSE"] = str(tmp_path / "ambo_test.duckdb")
    env["DBT_TARGET_PATH"] = str(tmp_path / "dbt_target")
    return env


def _run_dbt_on_tree(
    repo_root: Path, source_tree: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Run the `test`-target dbt build with `data_synthetic_path` pointed at
    `source_tree`.

    `source_tree` is rendered with `Path.as_posix()` before being embedded in the
    `--vars` JSON string -- a raw Windows path's backslashes are invalid JSON escape
    sequences, which would produce a red run for the wrong reason (T-03-11,
    RESEARCH.md Pitfall 4)."""
    vars_json = json.dumps({"data_synthetic_path": source_tree.as_posix()})
    return subprocess.run(
        [*_DBT_BUILD_PREFIX, "--target", "test", "--vars", vars_json],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def _real_warehouse_mtime(repo_root: Path) -> float | None:
    real_warehouse = repo_root / "data" / "warehouse" / "ambo.duckdb"
    return real_warehouse.stat().st_mtime if real_warehouse.is_file() else None


def test_clean_fixture_tree_builds_green(
    repo_root: Path, tmp_path: Path, synthetic_tree_copy: Path
) -> None:
    """Control run: the untouched copied tree builds green.

    Proves the harness itself -- the tmp warehouse, the tmp target path, the
    `data_synthetic_path` var override, the `--vars` JSON quoting -- is not what
    would turn the next test red (T-03-09)."""
    mtime_before = _real_warehouse_mtime(repo_root)
    env = _dbt_env(tmp_path)

    result = _run_dbt_on_tree(repo_root, synthetic_tree_copy, env)
    combined = result.stdout + result.stderr
    tail = "\n".join(combined.splitlines()[-40:])

    assert result.returncode == 0, (
        "clean-tree control build failed -- this means the harness itself (tmp "
        "warehouse, tmp target path, --vars JSON quoting) is broken, not the grain "
        f"test under proof. Last 40 lines of output:\n{tail}"
    )

    tmp_warehouse = Path(env["AMBO_TEST_WAREHOUSE"])
    assert tmp_warehouse.is_file(), (
        f"expected a tmp warehouse at {tmp_warehouse} after a green build -- the "
        f"`test` target's --vars override may not be reaching profiles.yml. Last 40 "
        f"lines of output:\n{tail}"
    )

    assert _real_warehouse_mtime(repo_root) == mtime_before, (
        "the real warehouse's modification time changed during the clean-tree "
        "control build -- the fixture run touched data/warehouse/ambo.duckdb "
        f"instead of staying inside {tmp_warehouse}."
    )


def test_duplicate_grain_key_fails_dbt_build(
    repo_root: Path, tmp_path: Path, synthetic_tree_copy: Path
) -> None:
    """Poisoned run: an exact duplicate (week_start, channel) row appended to
    `s_a/media_weekly.csv` makes `dbt build` fail on `stg_media_weekly`'s `unique`
    test -- proven by making it happen, not asserted from the test's mere presence
    (D-11, RESEARCH.md Pitfall 4)."""
    mtime_before = _real_warehouse_mtime(repo_root)
    env = _dbt_env(tmp_path)

    media_csv = synthetic_tree_copy / "s_a" / "media_weekly.csv"
    lines = media_csv.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 1, (
        f"{media_csv} has no data rows to duplicate -- the synthetic_tree_copy "
        "fixture itself is broken."
    )
    duplicate_line = lines[1]  # an existing (week_start, channel) data row
    with media_csv.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(duplicate_line + "\n")

    result = _run_dbt_on_tree(repo_root, synthetic_tree_copy, env)
    combined = result.stdout + result.stderr
    tail = "\n".join(combined.splitlines()[-40:])

    assert result.returncode != 0, (
        "poisoned-tree build exited 0 -- appending an exact duplicate "
        "(week_start, channel) row to s_a/media_weekly.csv did not fail `dbt "
        f"build`; the grain-uniqueness proof did not fire. Last 40 lines of "
        f"output:\n{tail}"
    )

    assert "unique_stg_media_weekly" in combined, (
        "the poisoned-tree build exited non-zero, but the captured output does not "
        "name the stg_media_weekly unique test node -- a red exit from an "
        "unrelated cause must not be mistaken for proof the grain test fired "
        f"(T-03-09). Last 40 lines of output:\n{tail}"
    )

    for error_marker in ("Compilation Error", "Parsing Error", "IO Error", "No such file"):
        assert error_marker not in combined, (
            f"the poisoned-tree build's output contains {error_marker!r}, which "
            "would mean the red exit is caused by a compilation or IO failure "
            "rather than the stg_media_weekly unique test firing (T-03-09). Last "
            f"40 lines of output:\n{tail}"
        )

    assert _real_warehouse_mtime(repo_root) == mtime_before, (
        "the real warehouse's modification time changed during the poisoned-tree "
        "build -- the fixture run touched data/warehouse/ambo.duckdb instead of "
        f"staying inside {env['AMBO_TEST_WAREHOUSE']}."
    )

    tmp_warehouse = Path(env["AMBO_TEST_WAREHOUSE"])
    assert tmp_warehouse.is_file(), (
        f"expected a tmp warehouse at {tmp_warehouse} even though the build "
        "failed -- the staging views build successfully before the `unique` test "
        f"runs against them, so the tmp duckdb file should still exist. Last 40 "
        f"lines of output:\n{tail}"
    )


# --- AD-042 reconciliation and AD-040 spine ordering (plan 03-04) ------------------
#
# Independent, Python-side checks against the built mart. `test_mart_revenue_matches
# _simulator_csv_sums` compares the mart to three literal sums verified from the
# committed CSVs at planning time, so a change that corrupted both the mart and the
# dbt singular test's CSV read identically would still be caught. `test_weekly_spine
# _is_gapless_and_ascending` is the ordering half of the spine guarantee -- the dbt
# `ad040_gapless_week_spine` test proves no week is missing; this test proves the
# sequence a consumer sees is monotonic with a uniform seven-day step.

# Verified from the committed s_a/s_b/s_c outcome_weekly.csv files at planning time
# (03-RESEARCH.md Pattern 4) -- independent of both the mart and the dbt singular
# test's own CSV read.
_EXPECTED_REVENUE_SUMS: dict[str, float] = {
    "P-SA": 14893565.459516,
    "P-SB": 9794127.034897,
    "P-SC": 6992687.768258,
}
_EXPECTED_ROW_COUNTS: dict[str, int] = {
    "P-SA": 156,
    "P-SB": 104,
    "P-SC": 78,
}
_REVENUE_TOLERANCE = 1e-6


def test_mart_revenue_matches_simulator_csv_sums(repo_root: Path) -> None:
    """Per-layer revenue sums and row counts against three literals independently
    verified from the committed CSVs at planning time -- never re-derived from the
    CSVs at test time, unlike the dbt `ad042_revenue_reconciliation` singular test
    this deliberately duplicates (T-03-04 AD-042)."""
    result = _run_dbt(repo_root)
    tail = "\n".join(result.stdout.splitlines()[-40:])
    assert result.returncode == 0, (
        f"dbt build failed before the AD-042 assertion could run. Last 40 lines of stdout:\n{tail}"
    )

    warehouse_path = load_settings().paths.warehouse
    con = duckdb.connect(str(warehouse_path), read_only=True)
    try:
        for layer, expected_sum in _EXPECTED_REVENUE_SUMS.items():
            actual_sum, row_count = con.execute(
                "select sum(revenue), count(*) from fct_mmm_input where layer = ?",
                [layer],
            ).fetchone()
            assert abs(actual_sum - expected_sum) <= _REVENUE_TOLERANCE, (
                f"layer={layer!r}: mart revenue sum {actual_sum} does not match the "
                f"literal expected sum {expected_sum} within {_REVENUE_TOLERANCE} "
                f"(delta={abs(actual_sum - expected_sum)})"
            )
            assert row_count == _EXPECTED_ROW_COUNTS[layer], (
                f"layer={layer!r}: mart row count {row_count} does not match the "
                f"expected count {_EXPECTED_ROW_COUNTS[layer]}"
            )
    finally:
        con.close()


def test_weekly_spine_is_gapless_and_ascending(repo_root: Path) -> None:
    """For each of the three P layers, week_start read ascending is strictly
    increasing with a uniform seven-day step -- the ordering half of the spine
    guarantee (the dbt `ad040_gapless_week_spine` test proves no week is missing;
    this proves the sequence is monotonic)."""
    result = _run_dbt(repo_root)
    tail = "\n".join(result.stdout.splitlines()[-40:])
    assert result.returncode == 0, (
        f"dbt build failed before the AD-040 ordering assertion could run. Last 40 "
        f"lines of stdout:\n{tail}"
    )

    warehouse_path = load_settings().paths.warehouse
    con = duckdb.connect(str(warehouse_path), read_only=True)
    try:
        for layer, expected_count in _EXPECTED_ROW_COUNTS.items():
            weeks: list[datetime.date] = [
                row[0]
                for row in con.execute(
                    "select week_start from fct_mmm_input where layer = ? order by week_start asc",
                    [layer],
                ).fetchall()
            ]
            assert len(weeks) == expected_count, (
                f"layer={layer!r}: expected {expected_count} weeks, got {len(weeks)}"
            )
            for previous, current in itertools.pairwise(weeks):
                assert current > previous, (
                    f"layer={layer!r}: week_start sequence is not strictly "
                    f"increasing at {previous} -> {current}"
                )
                gap = (current - previous).days
                assert gap == 7, (
                    f"layer={layer!r}: non-seven-day gap of {gap} day(s) between "
                    f"{previous} and {current}"
                )
    finally:
        con.close()
