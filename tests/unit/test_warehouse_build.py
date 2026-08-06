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


# --- dim_layer.channels_present (D-13/D-14, plan 03-05) ----------------------------
#
# Two Python-side checks, independent of the dbt tests, pinning the Phase 4
# interface: channels_present is taxonomy-ordered against config/settings.yaml
# (never a hard-coded literal here), and the absent-versus-ineffective distinction
# is asserted by name on the one layer where it matters most (P-SC's display_video
# vs. `other`). A third, fixture-driven test proves the derivation responds to
# source-row presence rather than being a constant.


def test_channels_present_is_taxonomy_ordered_and_source_derived(repo_root: Path) -> None:
    """For each Layer P row, channels_present splits into exactly six tokens that
    are a subsequence of load_settings().channels in the same relative order -- the
    ordering authority is config/settings.yaml, never a literal in this test, so a
    sanctioned future taxonomy change does not falsely fail this test while a
    reordering still does -- and `other` is never among them (BP-D-04)."""
    result = _run_dbt(repo_root)
    tail = "\n".join(result.stdout.splitlines()[-40:])
    assert result.returncode == 0, (
        f"dbt build failed before the channels_present assertion could run. Last 40 "
        f"lines of stdout:\n{tail}"
    )

    settings_channels = load_settings().channels

    warehouse_path = load_settings().paths.warehouse
    con = duckdb.connect(str(warehouse_path), read_only=True)
    try:
        rows = con.execute(
            "select layer, channels_present from dim_layer order by layer"
        ).fetchall()
    finally:
        con.close()

    assert len(rows) == 3, f"expected 3 dim_layer rows, got {len(rows)}: {rows}"

    for layer, channels_present in rows:
        tokens = channels_present.split(",")
        assert len(tokens) == 6, (
            f"layer={layer!r}: expected 6 tokens in channels_present, got "
            f"{len(tokens)}: {channels_present!r}"
        )
        assert "other" not in tokens, (
            f"layer={layer!r}: 'other' present in channels_present "
            f"{channels_present!r} -- 'other' is Layer-R-only (BP-D-04)"
        )
        last_position = -1
        for token in tokens:
            assert token in settings_channels, (
                f"layer={layer!r}: token {token!r} not present in "
                f"load_settings().channels {settings_channels!r}"
            )
            position = settings_channels.index(token)
            assert position > last_position, (
                f"layer={layer!r}: channels_present {channels_present!r} is not a "
                f"taxonomy-ordered subsequence of load_settings().channels "
                f"{settings_channels!r}"
            )
            last_position = position


def test_absent_channel_and_ineffective_channel_are_distinguishable(
    repo_root: Path,
) -> None:
    """P-SC: display_video is present with real spend (present-but-ineffective --
    zero true effect by VR-304 design) while `other` is absent with spend_other
    exactly 0.0 on every row (structurally absent). These two states must never be
    conflated -- MD-040's channel-agnostic priors would otherwise fit a coefficient
    for a channel with no data at all."""
    result = _run_dbt(repo_root)
    tail = "\n".join(result.stdout.splitlines()[-40:])
    assert result.returncode == 0, (
        f"dbt build failed before the distinguishability assertion could run. Last "
        f"40 lines of stdout:\n{tail}"
    )

    warehouse_path = load_settings().paths.warehouse
    con = duckdb.connect(str(warehouse_path), read_only=True)
    try:
        channels_present = con.execute(
            "select channels_present from dim_layer where layer = 'P-SC'"
        ).fetchone()[0]
        display_video_total, other_total, other_nonzero_count, row_count = con.execute(
            """
            select
                sum(spend_display_video),
                sum(spend_other),
                count(*) filter (where spend_other <> 0.0),
                count(*)
            from fct_mmm_input
            where layer = 'P-SC'
            """
        ).fetchone()
    finally:
        con.close()

    assert row_count == 78, f"expected 78 P-SC rows, got {row_count}"

    tokens = channels_present.split(",")
    assert "display_video" in tokens, (
        f"'display_video' not listed in P-SC's channels_present "
        f"{channels_present!r} -- present-but-ineffective and structurally-absent "
        "must never be conflated"
    )
    assert display_video_total > 0, (
        f"P-SC spend_display_video total is {display_video_total}, expected > 0 -- "
        "display_video is present-but-ineffective (VR-304: real spend, zero true "
        "effect by design), not structurally absent; this total must never be "
        "conflated with an absent channel's zero"
    )

    assert "other" not in tokens, (
        f"'other' listed in P-SC's channels_present {channels_present!r} -- 'other' "
        "is structurally absent for every Layer P layer (BP-D-04) and must never "
        "be conflated with a present-but-ineffective channel"
    )
    assert other_total == 0.0 and other_nonzero_count == 0, (
        f"P-SC spend_other total is {other_total} with {other_nonzero_count} "
        f"nonzero row(s) out of {row_count} -- 'other' is structurally absent and "
        "must be exactly 0.0 on every row, never conflated with a "
        "present-but-ineffective channel's real spend"
    )


def test_channels_present_responds_to_source_row_removal(
    repo_root: Path, tmp_path: Path, synthetic_tree_copy: Path
) -> None:
    """Deletes every radio row from the tmp-copied s_a/media_weekly.csv, builds
    against the poisoned tree, and asserts dim_layer's P-SA row lists five channels
    without radio and spend_radio is 0.0 on every P-SA fct_mmm_input row --  proving
    the derivation responds to source-row presence rather than being a constant
    (D-13)."""
    env = _dbt_env(tmp_path)

    media_csv = synthetic_tree_copy / "s_a" / "media_weekly.csv"
    lines = media_csv.read_text(encoding="utf-8").splitlines()
    header, data_lines = lines[0], lines[1:]
    filtered = [line for line in data_lines if ",radio," not in line]
    assert len(filtered) < len(data_lines), (
        f"{media_csv} had no radio rows to remove -- the synthetic_tree_copy "
        "fixture itself is broken."
    )
    media_csv.write_text("\n".join([header, *filtered]) + "\n", encoding="utf-8", newline="\n")

    result = _run_dbt_on_tree(repo_root, synthetic_tree_copy, env)
    combined = result.stdout + result.stderr
    tail = "\n".join(combined.splitlines()[-40:])
    assert result.returncode == 0, (
        "radio-removed tree build failed unexpectedly -- no grain constraint "
        f"depends on radio's presence, so this build should stay green. Last 40 "
        f"lines of output:\n{tail}"
    )

    tmp_warehouse = Path(env["AMBO_TEST_WAREHOUSE"])
    con = duckdb.connect(str(tmp_warehouse), read_only=True)
    try:
        channels_present = con.execute(
            "select channels_present from dim_layer where layer = 'P-SA'"
        ).fetchone()[0]
        nonzero_radio_count = con.execute(
            "select count(*) from fct_mmm_input where layer = 'P-SA' and spend_radio <> 0.0"
        ).fetchone()[0]
    finally:
        con.close()

    tokens = channels_present.split(",")
    assert len(tokens) == 5, (
        f"expected 5 channels in P-SA's channels_present after removing every "
        f"radio source row, got {len(tokens)}: {channels_present!r}"
    )
    assert "radio" not in tokens, (
        f"'radio' still listed in P-SA's channels_present {channels_present!r} "
        "after every radio source row was removed -- channels_present is not "
        "responding to source-row presence"
    )
    assert nonzero_radio_count == 0, (
        f"{nonzero_radio_count} P-SA row(s) have nonzero spend_radio after every "
        "radio source row was removed from the source tree"
    )


# --- D-20 Layer R fixture run (plan 03-06) ------------------------------------------
#
# The one dbt invocation in this repository that actually sets `layer_r_present:
# true` and exercises the `layer_r_present` jinja branch end-to-end (raw -> staging
# -> marts, every contract, every AD-040/041/043 and both-directions test) against a
# small, obviously-fake fixture -- so Phase 6 inherits a path that has already run
# rather than flipping a flag onto dead SQL for the first time in a phase that also
# carries a permission gate, a prior freeze, and real client data (AGENTS A-2, A-4).
# `data/real_anon/` itself stays empty this phase; the fixture lives under
# `tests/fixtures/real_anon_fake/`, committed and scanned by `scripts/leak_scan.py`
# like every other tracked file.

_LAYER_R_FIXTURE_RELATIVE = Path("tests") / "fixtures" / "real_anon_fake"


def _run_dbt_with_layer_r_fixture(
    repo_root: Path, fixture_dir: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Run the `test`-target dbt build with `layer_r_present` true and
    `data_real_anon_path` pointed at `fixture_dir`.

    `fixture_dir` is rendered with `Path.as_posix()` before being embedded in the
    `--vars` JSON string, for the same reason `_run_dbt_on_tree` does -- a raw
    Windows path's backslashes are invalid JSON escape sequences (T-03-11,
    RESEARCH.md Pitfall 4)."""
    vars_json = json.dumps({"layer_r_present": True, "data_real_anon_path": fixture_dir.as_posix()})
    return subprocess.run(
        [*_DBT_BUILD_PREFIX, "--target", "test", "--vars", vars_json],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_layer_r_branch_builds_green_against_fixture(repo_root: Path, tmp_path: Path) -> None:
    """D-20: one full `dbt build` with `layer_r_present: true` and
    `data_real_anon_path` pointed at the committed fake fixture builds every raw,
    staging and mart model green, including all contracts and the AD-040/041/043
    and both-directions tests, on a four-layer warehouse. A red result here is the
    finding this plan exists to produce -- diagnosable from the captured output
    without re-running."""
    mtime_before = _real_warehouse_mtime(repo_root)
    env = _dbt_env(tmp_path)
    fixture_dir = repo_root / _LAYER_R_FIXTURE_RELATIVE

    result = _run_dbt_with_layer_r_fixture(repo_root, fixture_dir, env)
    combined = result.stdout + result.stderr
    tail = "\n".join(combined.splitlines()[-40:])

    assert result.returncode == 0, (
        f"layer_r_present fixture build exited {result.returncode}, expected 0 -- "
        "every raw, staging and mart model plus every contract and the "
        "AD-040/041/043 and both-directions tests must build green with the flag "
        f"on (D-20). Last 40 lines of output:\n{tail}"
    )

    tmp_warehouse = Path(env["AMBO_TEST_WAREHOUSE"])
    con = duckdb.connect(str(tmp_warehouse), read_only=True)
    try:
        dim_layer_rows = con.execute(
            "select layer, weeks, monetary_unit, source_tag, channels_present "
            "from dim_layer order by layer"
        ).fetchall()
        assert len(dim_layer_rows) == 4, (
            "expected 4 dim_layer rows (three Layer P plus Layer R) with the flag "
            f"on, got {len(dim_layer_rows)}: {dim_layer_rows}. Last 40 lines of "
            f"output:\n{tail}"
        )
        r_row = next((row for row in dim_layer_rows if row[0] == "R"), None)
        assert r_row is not None, (
            f"no layer='R' row in dim_layer with the flag on: {dim_layer_rows}. "
            f"Last 40 lines of output:\n{tail}"
        )
        _, weeks, monetary_unit, source_tag, channels_present = r_row
        assert weeks == 12, f"layer R weeks={weeks}, expected 12. Last 40 lines of output:\n{tail}"
        assert monetary_unit == "aEUR", (
            f"layer R monetary_unit={monetary_unit!r}, expected 'aEUR'. Last 40 "
            f"lines of output:\n{tail}"
        )
        assert source_tag == "REAL-ANON", (
            f"layer R source_tag={source_tag!r}, expected 'REAL-ANON'. Last 40 "
            f"lines of output:\n{tail}"
        )
        assert channels_present == "search_brand,meta,other", (
            f"layer R channels_present={channels_present!r}, expected "
            f"'search_brand,meta,other' (taxonomy order). Last 40 lines of "
            f"output:\n{tail}"
        )

        total_rows, r_rows = con.execute(
            "select count(*), count(*) filter (where layer = 'R') from fct_mmm_input"
        ).fetchone()
        assert total_rows == 350, (
            f"fct_mmm_input total row count is {total_rows}, expected 350 (338 "
            f"Layer P + 12 Layer R). Last 40 lines of output:\n{tail}"
        )
        assert r_rows == 12, (
            f"fct_mmm_input layer='R' row count is {r_rows}, expected 12. Last 40 "
            f"lines of output:\n{tail}"
        )

        (
            spend_other_min,
            radio_nonzero,
            search_generic_nonzero,
            display_video_nonzero,
            print_regional_nonzero,
        ) = con.execute(
            """
            select
                min(spend_other),
                count(*) filter (where spend_radio <> 0.0),
                count(*) filter (where spend_search_generic <> 0.0),
                count(*) filter (where spend_display_video <> 0.0),
                count(*) filter (where spend_print_regional <> 0.0)
            from fct_mmm_input
            where layer = 'R'
            """
        ).fetchone()
        assert spend_other_min is not None and spend_other_min > 0, (
            f"layer R spend_other minimum is {spend_other_min}, expected > 0 on "
            f"every row. Last 40 lines of output:\n{tail}"
        )
        zero_channel_counts = (
            radio_nonzero,
            search_generic_nonzero,
            display_video_nonzero,
            print_regional_nonzero,
        )
        assert zero_channel_counts == (0, 0, 0, 0), (
            "layer R rows have nonzero spend on a channel outside the fixture's "
            f"three-channel taxonomy subset: spend_radio nonzero={radio_nonzero}, "
            f"spend_search_generic nonzero={search_generic_nonzero}, "
            f"spend_display_video nonzero={display_video_nonzero}, "
            f"spend_print_regional nonzero={print_regional_nonzero}. Last 40 lines "
            f"of output:\n{tail}"
        )

        platform_reported_count = con.execute(
            "select count(*) from fct_platform_reported"
        ).fetchone()[0]
        assert platform_reported_count == 2064, (
            f"fct_platform_reported row count is {platform_reported_count}, "
            f"expected 2064 (2028 Layer P + 36 Layer R). Last 40 lines of "
            f"output:\n{tail}"
        )
    finally:
        con.close()

    assert _real_warehouse_mtime(repo_root) == mtime_before, (
        "the real warehouse's modification time changed during the "
        "layer_r_present fixture build -- the run touched "
        f"data/warehouse/ambo.duckdb instead of staying inside {tmp_warehouse}. "
        f"Last 40 lines of output:\n{tail}"
    )
