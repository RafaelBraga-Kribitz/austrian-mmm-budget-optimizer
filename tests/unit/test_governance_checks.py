"""Tests for `scripts/check_layer_order.py` and `scripts/check_ssot_consistency.py`
(GB-501/GB-502, GB-301/GB-303; D-17): throwaway-repository proofs that both
governance checks pass and fail for the right reasons.

Implements: REQ-dl8-quality

Every throwaway repository below is built from scratch inside the `tmp_repo` fixture
(a fresh `git init` with a local commit identity) -- nothing here touches the real
repository's history. `main()` is invoked directly with `--root <tmp_repo>` rather
than shelled out to a subprocess, so a failure surfaces as an ordinary pytest
traceback.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import check_layer_order  # noqa: E402
import check_ssot_consistency  # noqa: E402


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _commit(repo: Path, rel_path: str, content: str, message: str) -> str:
    """Write `rel_path` inside `repo`, `git add` + `git commit` it, and return the
    new commit's full SHA."""
    _write(repo / rel_path, content)
    subprocess.run(["git", "add", rel_path], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=repo, check=True)
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _tag(repo: Path, tag: str) -> None:
    subprocess.run(["git", "tag", tag], cwd=repo, check=True)


# ---------------------------------------------------------------------------
# check_layer_order.py -- GB-501 / GB-502
# ---------------------------------------------------------------------------


def test_layer_order_artifact_free_repo_passes_with_nothing_to_check_notice(
    tmp_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _commit(tmp_repo, "README.md", "# scratch\n", "chore: init")

    exit_code = check_layer_order.main(["--root", str(tmp_repo)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "no layer r" in captured.out.lower()
    assert "prior-freeze-v1" in captured.out


def test_layer_order_correct_order_passes(
    tmp_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _commit(
        tmp_repo,
        "config/priors_real.yaml",
        "search_brand: {mode: 0.3}\n",
        "feat: freeze real priors",
    )
    _commit(
        tmp_repo,
        "docs/PRIOR_ELICITATION.md",
        "# Prior elicitation\n",
        "docs: prior elicitation",
    )
    _tag(tmp_repo, "prior-freeze-v1")
    _commit(
        tmp_repo,
        "reports/recovery/RECOVERY_REPORT.md",
        "# Recovery report\nAll gates green.\n",
        "docs: recovery report",
    )
    _commit(
        tmp_repo,
        "data/posteriors/R_2026.parquet",
        "not a real parquet file -- just bytes for the test\n",
        "feat: layer r posterior",
    )

    exit_code = check_layer_order.main(["--root", str(tmp_repo)])
    captured = capsys.readouterr()

    assert exit_code == 0, captured.err
    assert "GB-501/GB-502" in captured.out or "checked against" in captured.out


def test_layer_order_fit_before_report_fails(
    tmp_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _commit(
        tmp_repo,
        "config/priors_real.yaml",
        "search_brand: {mode: 0.3}\n",
        "feat: freeze real priors",
    )
    _commit(
        tmp_repo,
        "docs/PRIOR_ELICITATION.md",
        "# Prior elicitation\n",
        "docs: prior elicitation",
    )
    _tag(tmp_repo, "prior-freeze-v1")
    _commit(
        tmp_repo,
        "data/posteriors/R_2026.parquet",
        "not a real parquet file -- just bytes for the test\n",
        "feat: layer r posterior",
    )
    _commit(
        tmp_repo,
        "reports/recovery/RECOVERY_REPORT.md",
        "# Recovery report\nAll gates green.\n",
        "docs: recovery report",
    )

    exit_code = check_layer_order.main(["--root", str(tmp_repo)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "GB-501" in captured.err


def test_layer_order_artifact_without_freeze_tag_fails_on_gb502(
    tmp_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _commit(
        tmp_repo,
        "reports/recovery/RECOVERY_REPORT.md",
        "# Recovery report\nAll gates green.\n",
        "docs: recovery report",
    )
    _commit(
        tmp_repo,
        "data/posteriors/R_2026.parquet",
        "not a real parquet file -- just bytes for the test\n",
        "feat: layer r posterior",
    )

    exit_code = check_layer_order.main(["--root", str(tmp_repo)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "GB-502" in captured.err
    assert "prior-freeze-v1" in captured.err


def test_first_commit_adding_returns_none_when_path_never_added(tmp_repo: Path) -> None:
    _commit(tmp_repo, "README.md", "# scratch\n", "chore: init")

    assert check_layer_order.first_commit_adding("nonexistent.txt", tmp_repo) is None


def test_first_commit_adding_returns_the_initial_add_commit(tmp_repo: Path) -> None:
    first = _commit(tmp_repo, "docs/notes.md", "v1\n", "docs: v1")
    _commit(tmp_repo, "docs/notes.md", "v1\nv2\n", "docs: v2")

    assert check_layer_order.first_commit_adding("docs/notes.md", tmp_repo) == first


def test_diff_is_append_only_handles_the_repository_root_commit(tmp_repo: Path) -> None:
    """WR-03: `commit^` does not resolve when `commit` is the repository's very
    first commit -- the old code let `subprocess.CalledProcessError` propagate
    uncaught out of `_git`'s `check=True`, breaking the documented exit-code
    contract. A root commit's own diff must be treated as a full (trivially
    append-only) addition instead of crashing."""
    root_commit = _commit(
        tmp_repo,
        "docs/PRIOR_ELICITATION.md",
        "# Prior elicitation\n\n## Amendment 2026-08-05\nline one\n",
        "docs: initial prior elicitation",
    )

    append_only, hunk_starts = check_layer_order._diff_is_append_only(
        tmp_repo, root_commit, "docs/PRIOR_ELICITATION.md"
    )

    assert append_only is True
    assert hunk_starts  # the whole file was added, so at least one hunk start


# ---------------------------------------------------------------------------
# check_ssot_consistency.py -- GB-301 / GB-302 / GB-303
# ---------------------------------------------------------------------------

_WELL_FORMED_SSOT = """\
# Numeric SSOT

| key | value | unit | tag | produced_by | updated_at |
|---|---|---|---|---|---|
| recovery_pass_sa | true | bool | CALIBRATED | recover.py | 2026-08-04 |
| holdout_mape_real | 12.3 | % | MODELED | holdout.py | 2026-08-04 |
"""

_MALFORMED_SSOT_MISSING_COLUMN = """\
# Numeric SSOT

| key | value | unit | tag | produced_by |
|---|---|---|---|---|
| recovery_pass_sa | true | bool | CALIBRATED | recover.py |
"""


def test_ssot_absent_file_passes_with_nothing_to_reconcile_notice(
    tmp_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _commit(tmp_repo, "README.md", "# scratch\n", "chore: init")

    exit_code = check_ssot_consistency.main(["--root", str(tmp_repo)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "NUMERIC_SSOT.md" in captured.out


def test_ssot_well_formed_table_parses_to_expected_row_count(tmp_repo: Path) -> None:
    ssot_path = tmp_repo / "reports" / "NUMERIC_SSOT.md"
    _write(ssot_path, _WELL_FORMED_SSOT)

    rows = check_ssot_consistency.parse_ssot(ssot_path)

    assert len(rows) == 2
    assert set(rows) == {"recovery_pass_sa", "holdout_mape_real"}


def test_ssot_malformed_table_missing_column_exits_non_zero(
    tmp_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tmp_repo / "reports" / "NUMERIC_SSOT.md", _MALFORMED_SSOT_MISSING_COLUMN)

    exit_code = check_ssot_consistency.main(["--root", str(tmp_repo)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err  # an error was printed, not silence


# ---------------------------------------------------------------------------
# check_ssot_consistency.py -- _matches_any_row unit-normalization symmetry
# (WR-01) and ambiguous decimal-comma rejection (WR-02)
# ---------------------------------------------------------------------------


def test_matches_any_row_reconciles_multiplier_symbol_across_x_and_times() -> None:
    """WR-01: a literal spelled `×` must still reconcile against an SSOT row
    spelled `x` (and vice versa) -- normalizing only the literal's unit and never
    the row's meant a value that should reconcile was reported as unmatched."""
    rows = {
        "k": {
            "key": "k",
            "value": "8",
            "unit": "x",
            "tag": "T",
            "produced_by": "p",
            "updated_at": "d",
        }
    }

    assert check_ssot_consistency._matches_any_row("8", "×", rows) is True


def test_matches_any_row_reconciles_multiplier_symbol_the_other_direction() -> None:
    rows = {
        "k": {
            "key": "k",
            "value": "8",
            "unit": "×",
            "tag": "T",
            "produced_by": "p",
            "updated_at": "d",
        }
    }

    assert check_ssot_consistency._matches_any_row("8", "x", rows) is True


def test_matches_any_row_rejects_a_bare_decimal_comma_literal() -> None:
    """WR-02: `234,56` comma-stripped is `23456` -- a silent wrong-magnitude
    misparse, not a raised error, under the old code. It must now be rejected
    explicitly."""
    rows: dict[str, dict[str, str]] = {}

    with pytest.raises(check_ssot_consistency.SsotError, match="decimal comma"):
        check_ssot_consistency._matches_any_row("234,56", "%", rows)


def test_matches_any_row_rejects_an_austrian_formatted_literal() -> None:
    """WR-02: `1.234,56` comma-stripped is `1.234.56` -- `float()` raises
    `ValueError`, which the old code silently treated as "no match". It must now
    be rejected explicitly instead."""
    rows: dict[str, dict[str, str]] = {}

    with pytest.raises(check_ssot_consistency.SsotError, match="decimal comma"):
        check_ssot_consistency._matches_any_row("1.234,56", "%", rows)


def test_matches_any_row_rejects_an_austrian_formatted_ssot_row_value() -> None:
    """WR-02 applies symmetrically to the SSOT row's own value, not just the
    document literal -- an Austrian-formatted row value is just as ambiguous."""
    rows = {
        "k": {
            "key": "k",
            "value": "1.234,56",
            "unit": "%",
            "tag": "T",
            "produced_by": "p",
            "updated_at": "d",
        }
    }

    with pytest.raises(check_ssot_consistency.SsotError, match="decimal comma"):
        check_ssot_consistency._matches_any_row("1234.56", "%", rows)


def test_matches_any_row_accepts_well_formed_thousands_comma() -> None:
    """A genuine thousands-grouping comma (always followed by exactly three
    digits) is not ambiguous and must still reconcile as before."""
    rows = {
        "k": {
            "key": "k",
            "value": "1,234.56",
            "unit": "%",
            "tag": "T",
            "produced_by": "p",
            "updated_at": "d",
        }
    }

    assert check_ssot_consistency._matches_any_row("1,234.56", "%", rows) is True
