"""Tests for `scripts/leak_scan.py` (T-008): all three modes, all three pattern
classes, both scoping directions, and the never-echo-the-match contract.

Implements: REQ-scope-out, REQ-dl8-quality

Every fixture value below is invented for this module: an obviously fictional
`.invalid`-domain email, an obviously fictional Austrian phone number, an obviously
fictional currency figure, an obviously fictional drop path and blocklist token. None
is copied from anywhere. AG-032 and EB-071 apply to these fixtures precisely because
they are the values a detector is proven against — a fixture that proves a detector
works must never be the thing the detector exists to find. Every scan target is built
inside `tmp_repo`, so the real working tree is never touched.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from ambo.common.config import load_settings

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import leak_scan  # noqa: E402

# Fictional fixture values -- invented for this module, never real (AG-032/EB-071).
FICTIONAL_EMAIL = "kontakt@beispiel-marketingagentur.invalid"
FICTIONAL_CURRENCY = "€ 12.345,67"
FICTIONAL_DROP_PATH = "D:/fictional/never-real/ambo_drop_fixture"
FICTIONAL_BLOCKLIST_VALUE = "FICTIONAL-BLOCKLIST-TOKEN-Q7X9"


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    """Every test starts and ends with a cold `load_settings` cache, so a test that
    sets `AMBO_PRIVATE_DROP` genuinely changes what the scanner resolves."""
    load_settings.cache_clear()
    yield
    load_settings.cache_clear()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _git_stage_only(repo: Path, rel_path: str, content: str) -> None:
    """Write `rel_path` inside `repo` and `git add` it -- staged, not committed."""
    _write(repo / rel_path, content)
    subprocess.run(["git", "add", rel_path], cwd=repo, check=True)


# ---------------------------------------------------------------------------
# Structural contract
# ---------------------------------------------------------------------------


def test_finding_has_no_field_that_could_hold_matched_text() -> None:
    assert leak_scan.Finding._fields == ("path", "line", "pattern_class", "match_hash")


# ---------------------------------------------------------------------------
# Contact class -- scoped to data/real_anon/ and reports/ingestion/
# ---------------------------------------------------------------------------


def test_contact_email_found_under_data_real_anon(tmp_repo: Path) -> None:
    _git_stage_only(tmp_repo, "data/real_anon/contacts.txt", f"contact: {FICTIONAL_EMAIL}\n")

    findings = leak_scan.scan_tree(tmp_repo)

    assert len(findings) == 1
    assert findings[0].pattern_class == "contact"
    assert findings[0].path == "data/real_anon/contacts.txt"


def test_contact_email_found_under_reports_ingestion(tmp_repo: Path) -> None:
    _git_stage_only(tmp_repo, "reports/ingestion/intake_log.txt", f"see {FICTIONAL_EMAIL}\n")

    findings = leak_scan.scan_tree(tmp_repo)

    assert len(findings) == 1
    assert findings[0].pattern_class == "contact"


def test_contact_email_ignored_outside_scoped_roots(tmp_repo: Path) -> None:
    """Same value, out-of-scope paths -- both directions of D-26's precision."""
    _git_stage_only(tmp_repo, "docs/notes.md", f"contact: {FICTIONAL_EMAIL}\n")
    _git_stage_only(tmp_repo, "exports/report.csv", f"contact,{FICTIONAL_EMAIL}\n")

    findings = leak_scan.scan_tree(tmp_repo)

    assert findings == [], f"Out-of-scope contact value unexpectedly flagged: {findings}"


# ---------------------------------------------------------------------------
# Currency-literal class -- scoped to notebook files only
# ---------------------------------------------------------------------------


def test_currency_literal_found_in_notebook(tmp_repo: Path) -> None:
    notebook_content = f'{{"cells": [{{"outputs": [{{"text": "{FICTIONAL_CURRENCY}"}}]}}]}}\n'
    _git_stage_only(tmp_repo, "notebooks/explore.ipynb", notebook_content)

    findings = leak_scan.scan_tree(tmp_repo)

    assert len(findings) == 1
    assert findings[0].pattern_class == "currency_literal"


def test_currency_literal_ignored_outside_notebooks(tmp_repo: Path) -> None:
    """Same literal, out-of-scope file types -- the currency class's other
    scoping direction."""
    _git_stage_only(tmp_repo, "notes.py", f"# spend was {FICTIONAL_CURRENCY}\n")
    _git_stage_only(tmp_repo, "notes.md", f"spend was {FICTIONAL_CURRENCY}\n")

    findings = leak_scan.scan_tree(tmp_repo)

    assert findings == [], f"Out-of-scope currency literal unexpectedly flagged: {findings}"


# ---------------------------------------------------------------------------
# Private-drop class -- whole tree, resolved fresh through load_settings()
# ---------------------------------------------------------------------------


def test_private_drop_literal_path_found_when_resolved_via_environment(
    tmp_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AMBO_PRIVATE_DROP", FICTIONAL_DROP_PATH)
    load_settings.cache_clear()  # the value is genuinely re-resolved, not cached stale

    _git_stage_only(
        tmp_repo, "notes/leftover.md", f"scratch note referencing {FICTIONAL_DROP_PATH}\n"
    )

    findings = leak_scan.scan_tree(tmp_repo)

    assert len(findings) == 1
    assert findings[0].pattern_class == "private_drop"


def test_env_example_carve_out_does_not_suppress_the_literal_check(
    tmp_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`.env.example` is excluded from the generic assignment-shape check (it is
    the one sanctioned home for a fictional `AMBO_PRIVATE_DROP=<path>` line), but
    the literal resolved-value check still covers it -- a real value pasted there
    by mistake is still a leak."""
    monkeypatch.setenv("AMBO_PRIVATE_DROP", FICTIONAL_DROP_PATH)
    load_settings.cache_clear()

    _git_stage_only(tmp_repo, ".env.example", f"AMBO_PRIVATE_DROP={FICTIONAL_DROP_PATH}\n")

    findings = leak_scan.scan_tree(tmp_repo)

    assert len(findings) == 1
    assert findings[0].pattern_class == "private_drop"
    assert findings[0].path == ".env.example"


# ---------------------------------------------------------------------------
# Redaction contract -- never echo the match, on either stream
# ---------------------------------------------------------------------------


def test_output_never_contains_the_planted_value_on_either_stream(
    tmp_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _git_stage_only(tmp_repo, "data/real_anon/contacts.txt", f"contact: {FICTIONAL_EMAIL}\n")

    exit_code = leak_scan.main(["--root", str(tmp_repo)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert FICTIONAL_EMAIL not in captured.out
    assert FICTIONAL_EMAIL not in captured.err
    assert "contact" in captured.out
    expected_hash = hashlib.sha256(FICTIONAL_EMAIL.encode("utf-8")).hexdigest()[:8]
    assert expected_hash in captured.out


# ---------------------------------------------------------------------------
# Full mode -- blocklist present, and blocklist absent (graceful skip)
# ---------------------------------------------------------------------------


def test_full_mode_finds_a_blocklisted_value(
    tmp_path: Path,
    tmp_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_drop = tmp_path / "fake_private_drop"
    fake_drop.mkdir()
    (fake_drop / "blocklist.txt").write_text(FICTIONAL_BLOCKLIST_VALUE + "\n", encoding="utf-8")
    monkeypatch.setenv("AMBO_PRIVATE_DROP", str(fake_drop))
    load_settings.cache_clear()

    _git_stage_only(tmp_repo, "somewhere/leftover.txt", f"value: {FICTIONAL_BLOCKLIST_VALUE}\n")

    exit_code = leak_scan.main(["--full", "--root", str(tmp_repo)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert any(" blocklist " in line for line in captured.out.splitlines())
    assert FICTIONAL_BLOCKLIST_VALUE not in captured.out


def test_full_mode_without_blocklist_file_runs_the_subset_with_a_notice(
    tmp_path: Path,
    tmp_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_drop_no_blocklist = tmp_path / "fake_private_drop_no_blocklist"
    fake_drop_no_blocklist.mkdir()
    monkeypatch.setenv("AMBO_PRIVATE_DROP", str(fake_drop_no_blocklist))
    load_settings.cache_clear()

    exit_code = leak_scan.main(["--full", "--root", str(tmp_repo)])
    captured = capsys.readouterr()

    assert exit_code == 0  # exits on the (empty, clean) subset result, not a failure
    assert "blocklist" in captured.err.lower()


# ---------------------------------------------------------------------------
# Staged mode -- staged value found, unstaged value ignored
# ---------------------------------------------------------------------------


def test_staged_mode_finds_staged_value_and_ignores_unstaged(
    tmp_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(leak_scan, "repo_root", lambda: tmp_repo)

    _git_stage_only(tmp_repo, "data/real_anon/staged.txt", f"contact: {FICTIONAL_EMAIL}\n")

    unstaged_path = tmp_repo / "data" / "real_anon" / "unstaged.txt"
    unstaged_path.parent.mkdir(parents=True, exist_ok=True)
    unstaged_path.write_text(f"contact: {FICTIONAL_EMAIL}\n", encoding="utf-8")
    # deliberately never `git add`ed

    findings = leak_scan.scan_staged()

    assert len(findings) == 1
    assert findings[0].path == "data/real_anon/staged.txt"


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------


def test_exit_codes_clean_finding_and_usage_error(tmp_repo: Path) -> None:
    assert leak_scan.main(["--root", str(tmp_repo)]) == 0

    _git_stage_only(tmp_repo, "data/real_anon/contacts.txt", f"contact: {FICTIONAL_EMAIL}\n")
    assert leak_scan.main(["--root", str(tmp_repo)]) == 1

    assert leak_scan.main(["--bogus-flag"]) == 2
