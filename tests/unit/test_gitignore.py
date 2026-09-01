"""EB-081 ignore-rule guard, converting T-003's manual probe into a test.

`tmp_repo` is not right here: the rules under test are *this repository's own*
`.gitignore`, so the test operates on the real working tree, but only through
non-destructive means -- every created file is removed in a `finally` block, and
`git status --porcelain` is asserted byte-identical before and after.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _is_ignored(repo_root: Path, relative_path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", relative_path],
        cwd=repo_root,
        capture_output=True,
    )
    return result.returncode == 0


def _porcelain_status(repo_root: Path) -> str:
    return subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def test_generated_paths_ignored_but_exports_csv_committed_by_design(repo_root: Path) -> None:
    created = [
        repo_root / "data" / "warehouse" / "probe.duckdb",
        repo_root / "data" / "cache" / "probe.bin",
        repo_root / "exports" / "probe.csv",
    ]
    before = _porcelain_status(repo_root)

    try:
        for path in created:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"")

        assert _is_ignored(repo_root, "data/warehouse/probe.duckdb"), (
            "data/warehouse/ must be ignored (EB-081)"
        )
        assert _is_ignored(repo_root, "data/cache/probe.bin"), (
            "data/cache/ must be ignored (EB-081)"
        )
        assert not _is_ignored(repo_root, "exports/probe.csv"), (
            "exports/*.csv is committed by design (EB-081, DL-1) -- it must not be ignored"
        )
    finally:
        for path in created:
            path.unlink(missing_ok=True)

    after = _porcelain_status(repo_root)
    assert after == before, "gitignore probe left the working tree changed after cleanup"


def test_remaining_eb081_ignore_rules_by_path(repo_root: Path) -> None:
    """The rest of the EB-081 list, checked by path only -- `git check-ignore`
    needs no file to exist on disk, so no scratch file is created for these."""
    ignored_paths = [
        "data/somewhere/probe.nc",
        "src/ambo/__pycache__/probe.pyc",
        "dbt/target/manifest.json",
        ".env",
    ]
    for rel in ignored_paths:
        assert _is_ignored(repo_root, rel), f"{rel} should be ignored per EB-081 but is not"


def test_committed_by_design_data_directories_are_not_ignored(repo_root: Path) -> None:
    not_ignored_paths = [
        "data/synthetic/probe.csv",
        "data/real_anon/probe.csv",
        "data/posteriors/probe.parquet",
    ]
    for rel in not_ignored_paths:
        assert not _is_ignored(repo_root, rel), (
            f"{rel} should NOT be ignored -- committed by design (EB-081)"
        )
