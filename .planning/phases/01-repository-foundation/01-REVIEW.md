---
phase: 01-repository-foundation
reviewed: 2026-08-04T00:00:00Z
depth: standard
files_reviewed: 44
files_reviewed_list:
  - .github/pull_request_template.md
  - .github/workflows/ci.yml
  - config/settings.yaml
  - dbt/seeds/season_windows.csv
  - docs/ADR/ADR-000_document-precedence-and-blueprint-defaults.md
  - docs/ADR/ADR-006_module-contracts-layout-and-citation-policy.md
  - docs/ADR/README.md
  - docs/ADR/TEMPLATE.md
  - docs/BUILD_LOG.md
  - docs/EXECUTION_BLUEPRINT/03_MODULES.md
  - docs/EXECUTION_BLUEPRINT/12_RISK_REGISTER.md
  - docs/MODULE_CONTRACTS.md
  - docs/RISK_REGISTER.md
  - docs/SPEC-01_ground_truth_simulator.md
  - docs/SPEC-04_mmm_model.md
  - docs/SPEC-05_validation_recovery.md
  - docs/SPEC-06_decision_layer.md
  - docs/SPEC-08_engineering.md
  - scripts/check_layer_order.py
  - scripts/check_ssot_consistency.py
  - scripts/generate_season_windows.py
  - scripts/leak_scan.py
  - src/ambo/__init__.py
  - src/ambo/common/__init__.py
  - src/ambo/common/config.py
  - src/ambo/common/errors.py
  - src/ambo/common/logging.py
  - src/ambo/decide/__init__.py
  - src/ambo/intake/__init__.py
  - src/ambo/model/__init__.py
  - src/ambo/report/__init__.py
  - src/ambo/simulate/__init__.py
  - src/ambo/validate/__init__.py
  - tests/conftest.py
  - tests/unit/test_config.py
  - tests/unit/test_forbidden_deps.py
  - tests/unit/test_gitignore.py
  - tests/unit/test_governance_checks.py
  - tests/unit/test_import_independence.py
  - tests/unit/test_leak_scan.py
  - tests/unit/test_line_endings.py
  - tests/unit/test_logging.py
  - tests/unit/test_no_requests.py
  - tests/unit/test_repo_layout.py
  - tests/unit/test_season_windows.py
findings:
  critical: 2
  warning: 4
  info: 1
  total: 7
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-08-04
**Depth:** standard
**Files Reviewed:** 44
**Status:** issues_found

## Summary

This phase is a repository-foundation phase (toolchain, governance docs, config/logging
modules, architectural guard tests, a leak scanner, and a six-job CI workflow), and the
bulk of the code is solid: the four already-documented cross-platform fixes (docstring
self-match, `D:/` `Path.resolve()` treated as relative on POSIX, and the needle
double-count) are genuinely fixed and covered by platform-branching tests. No stub or
empty `src/ambo/*` subpackage was flagged, per the phase scope.

Two real gaps remain in the two privacy/security controls this phase ships, both
exactly in the areas flagged for scrutiny:

1. `scripts/leak_scan.py`'s `.env.example` carve-out, combined with CI never setting
   `AMBO_PRIVATE_DROP`, means a real absolute path pasted into `.env.example` is never
   caught by the `leak` CI job under any circumstance — the literal-value check is a
   no-op (no env var set) and the generic-shape check is explicitly exempted for that
   file. This is the exact "can the carve-out be abused to hide a real secret" question
   the phase context asked to check, and the answer is yes.
2. `src/ambo/common/logging.py`'s `PrivatePathFilter` only redacts `record.msg` and
   `record.args` when they are `str` instances, and never touches `record.exc_info`/the
   rendered traceback text. `logger.exception(...)`, or any call that passes a `Path` or
   exception object directly as `msg`/an arg, bypasses redaction entirely.

Four further logic/robustness defects were found in the two governance scripts
(`check_ssot_consistency.py`, `check_layer_order.py`) and one test, none of which are
exercised today (M0 has no SSOT data and no Layer R history) but which are real,
provable bugs in code that ships now and that Phase 5+ will rely on unmodified.

## Critical Issues

### CR-01: `.env.example` leak-scan carve-out is a real, exploitable blind spot in CI

**File:** `scripts/leak_scan.py:117-139` (see also `.github/workflows/ci.yml:155-167`)
**Issue:** `PRIVATE_DROP_PATTERNS`'s generic-shape check is scoped by `_not_env_example`
(line 120), which exempts `.env.example` entirely. The *other* half of class 1, the
literal-value check driven by `_resolve_private_drop_needles()` (line 211), is not
file-scoped, but it resolves `load_settings().private_drop` — and the CI `leak` job
(`.github/workflows/ci.yml:155-167`) never sets `AMBO_PRIVATE_DROP`, so
`_resolve_private_drop_needles()` returns `[]` and that check is a no-op in CI.

The combination means: if a contributor accidentally pastes a real absolute path into
`.env.example` (i.e. the env var assigned `<a real absolute drive-rooted path>` instead
of the placeholder — spelled with angle brackets here so this report does not itself
trip the scanner, the same reason `leak_scan.py`'s own doc comment was reworded in
`2bb8b7c`), **neither**
check fires in CI — the generic-shape check is exempted for that file by design, and
the literal check has nothing to compare against because CI has no
`AMBO_PRIVATE_DROP` of its own. The `leak` job would report clean. This is precisely
the scenario `.env.example` exists to prevent (a real value landing where only a
placeholder belongs), and the current design provides no CI-side backstop for it.

Every existing test (`tests/unit/test_leak_scan.py::test_env_example_carve_out_does_not_suppress_the_literal_check`)
proves the literal check works, but only because the test itself sets
`AMBO_PRIVATE_DROP` to the same value it plants — it never proves (or exercises) the
CI configuration where the variable is unset, which is the actual condition under
which this file is scanned in production.
**Fix:** Either (a) require the generic-shape check to still validate that anything
after `AMBO_PRIVATE_DROP=`/`:` in `.env.example` matches a documented placeholder
shape (e.g. only `<abs-path>` literally, rejecting any other absolute-path-shaped
value), rather than exempting the file outright, or (b) run the leak scan's `--full`/
literal check against a small fixed set of known-bad shapes even when
`AMBO_PRIVATE_DROP` is unset in CI. Option (a) is cheaper and closes the gap without
requiring CI to carry a private value:
```python
_PLACEHOLDER_RE = re.compile(r"^<[^<>]+>$")


def _not_env_example_or_is_real_value(rel_posix: str, candidate: str) -> bool:
    if rel_posix != _ENV_EXAMPLE_PATH:
        return True
    return not _PLACEHOLDER_RE.match(candidate)
```

### CR-02: `PrivatePathFilter` does not redact exception tracebacks or non-`str` log values

**File:** `src/ambo/common/logging.py:66-88`
**Issue:** `_redact` (line 74) returns any non-`str` value unchanged:
```python
def _redact(value: object) -> object:
    if not isinstance(value, str):
        return value
    ...
```
This means: (1) a `Path` object or an exception instance passed directly as `msg` or
as a `%`-arg (e.g. `logger.info(private_drop_path)` or `logger.error("failed: %s",
os_error)`) is never redacted, because `record.getMessage()` stringifies it *after*
this filter has already run and declined to touch it; (2) `record.exc_info`/
`record.exc_text` — the traceback attached by `logger.exception(...)` or
`logger.warning(..., exc_info=True)` — is never inspected or redacted by this filter
at all. A `FileNotFoundError`/`PermissionError` raised while touching a file under
the private drop naturally embeds the real path in its own message; logging that
exception's traceback leaks the path verbatim to the log stream, defeating the
module's own stated invariant ("no code path here can print a match by accident" is
`leak_scan.py`'s contract, but `logging.py`'s own docstring makes the equivalent claim
for `PrivatePathFilter`, and `errors.py:18-23` explicitly assigns "redaction of
already-emitted log records" to this filter).

No existing test in `tests/unit/test_logging.py` exercises `logger.exception(...)` or
a non-`str` `msg`/arg, so this gap is untested as well as unfixed.
**Fix:** Redact `record.exc_text` (and format `record.exc_info` into text and redact
it before it's cached) in `filter()`, and fall back to `_redact(str(value))` for
non-`str` `msg`/args rather than returning them unchanged:
```python
def _redact(value: object) -> object:
    text = value if isinstance(value, str) else str(value)
    redacted = text
    for needle in needles:
        redacted = _redact_case_insensitive(redacted, needle, REDACTION_TOKEN)
    return redacted if isinstance(value, str) else redacted


# and, in filter():
if record.exc_info:
    record.exc_text = _redact(record.getMessage())  # placeholder; use
    # logging.Formatter().formatException(record.exc_info) then _redact() it,
    # caching the result onto record.exc_text so Formatter.format() reuses it.
```

## Warnings

### WR-01: SSOT unit-symbol normalization is asymmetric — `×` vs `x` never cross-match

**File:** `scripts/check_ssot_consistency.py:123-143`
**Issue:** `_matches_any_row` normalizes only the literal-side unit (`unit_norm = "×" if
unit in ("x", "×") else unit.lower()`, line 131) but never normalizes `row["unit"]`
(`row_unit = row["unit"].lower()`, line 133). If a document spells a multiplier as `×`
but the SSOT table's `unit` column (produced by a separate script) spells it `x`, or
vice versa, `unit_norm not in row_unit and row_unit not in unit_norm` is `True` for
both directions and the row is skipped — a value that should reconcile is reported as
an unmatched (failing) literal. Since GB-303 is a CI-blocking check (job `ssot`), this
would fail the build for a document/table pair that actually agree, purely due to
symbol-form drift between the two authors of those files.
**Fix:** Normalize both sides identically before comparing:
```python
def _normalize_unit(unit: str) -> str:
    return "×" if unit in ("x", "×") else unit.lower()


unit_norm = _normalize_unit(unit)
...
row_unit = _normalize_unit(row["unit"])
```

### WR-02: SSOT literal parsing assumes period-decimal formatting; Austrian comma-decimal input silently fails to match

**File:** `scripts/check_ssot_consistency.py:119-143`
**Issue:** `_matches_any_row` parses both the extracted literal and the SSOT row's
value with `float(value.replace(",", ""))` (lines 128, 137) — i.e. it treats `,` purely
as a thousands separator and `.` as the decimal point (US/UK convention). `_decimals`
(line 119-120) likewise only counts digits after a `.`. For a project whose domain
documents are Austrian (comma-decimal, period-thousands: `1.234,56`), a literal
written in that convention either raises inside the `try/except ValueError` (silently
treated as "no match", line 129/138) or, worse, is misparsed into a different
magnitude if it happens to still be numeric-looking after comma-stripping. This is
inert today (no reconciled document carries a tagged number at M0, per the module's
own docstring), but it is real, shipped logic that Phase 5 will rely on unmodified —
and the bug will silently fail every Austrian-formatted number the SSOT is meant to
reconcile, not raise an obvious error.
**Fix:** Decide and document one canonical numeric-literal format for
`RECONCILED_DOCS` and `reports/NUMERIC_SSOT.md` (most likely period-decimal, to match
this parser), and add a validation step that rejects an ambiguous or
Austrian-formatted literal explicitly rather than silently failing to match it; or,
if Austrian formatting must be supported, parse with locale-aware logic that
distinguishes thousands- from decimal-separators by position, not by a blind
`replace(",", "")`.

### WR-03: `check_layer_order.py` crashes uncaught on a root-commit edge case instead of reporting a clean exit code

**File:** `scripts/check_layer_order.py:59-61, 120-132`
**Issue:** `_diff_is_append_only` (line 125) runs
`git diff --unified=0 f"{commit}^" commit -- path`. If `commit` (an amendment commit
found by `_commits_touching`, line 212-214) happens to be the repository's very first
commit, `commit^` does not resolve, and `_git` (line 59-61, `check=True`) raises
`subprocess.CalledProcessError`, which propagates out of `main()` uncaught. The
module's own documented exit-code contract ("exit 0 clean, 1 violations found, 2
usage error", module docstring line 30) is silently broken in this case: the process
exits with an unhandled-exception traceback rather than a structured error, on
stdout/stderr in a form the CI job's log-reader was never designed to parse cleanly.
This path is untested — `tests/unit/test_governance_checks.py` never plants a repo
where the first commit itself touches `docs/PRIOR_ELICITATION.md` after a freeze tag
pointing at that same initial commit.
**Fix:** Guard the parent lookup explicitly and treat a parentless commit as a full
addition (trivially append-only, since there is nothing to remove from):
```python
def _diff_is_append_only(root: Path, commit: str, path: str) -> tuple[bool, list[int]]:
    parent_check = subprocess.run(
        ["git", "rev-parse", "--verify", "-q", f"{commit}^"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    base = f"{commit}^" if parent_check.returncode == 0 else _EMPTY_TREE_SHA
    diff = _git(root, "diff", "--unified=0", base, commit, "--", path)
    ...
```

### WR-04: `test_set_private_drop_resolves_to_a_path` does not actually exercise absolute-path resolution on POSIX

**File:** `tests/unit/test_config.py:87-94`
**Issue:** This test hardcodes `"D:/private/ambo_drop_fake"` (line 92) with no
`sys.platform` branch, unlike the equivalent fixtures in `tests/unit/test_leak_scan.py`
(`FICTIONAL_DROP_PATH`) and `tests/unit/test_logging.py` (`FAKE_PRIVATE_DROP`), both of
which explicitly branch on `sys.platform` with a comment explaining that a `D:/...`
literal is absolute on Windows but merely relative-looking on POSIX (the exact class
of bug `docs/BUILD_LOG.md`'s "01-09 fix-forward" entry records as already found and
fixed elsewhere). Because this test compares `Path("D:/...").resolve()` against
itself computed the same way twice, it happens to still pass on Linux — but it does so
by resolving the fixture as a *relative* path against `cwd` on that leg, not as an
absolute path, so on POSIX CI this test silently stops proving what its name claims
("resolves to a path" — specifically, an absolute private-drop path). The same fix
applied to the two sibling test files was not applied here.
**Fix:** Apply the same `sys.platform` branch used in `test_leak_scan.py`/
`test_logging.py`:
```python
FAKE_PRIVATE_DROP = (
    "D:/private/ambo_drop_fake" if sys.platform == "win32" else "/private/ambo_drop_fake"
)
...
monkeypatch.setenv("AMBO_PRIVATE_DROP", FAKE_PRIVATE_DROP)
settings = load_settings()
assert settings.private_drop == Path(FAKE_PRIVATE_DROP).resolve()
assert settings.private_drop.is_absolute()
```

## Info

### IN-01: `MODULE_CONTRACTS.md` misdescribes `AMBO_LOG_LEVEL`'s scope

**File:** `docs/MODULE_CONTRACTS.md:108`
**Issue:** The contract for `src/ambo/common/logging.py` states `AMBO_LOG_LEVEL` "sets
the root logger's level." The implementation (`src/ambo/common/logging.py:115-117`)
sets the level on the specific named logger returned by `get_logger(name)`, never on
`logging.getLogger()` (the actual root logger) — each `get_logger()` call reads and
applies the env var to that logger instance only. The distinction matters: Python's
root logger and a named logger have independent effective levels, and a reader could
reasonably assume from this contract that one `AMBO_LOG_LEVEL` setting configures a
single global level rather than being re-applied per named logger on every
`get_logger()` call.
**Fix:** Reword to "sets the level of every logger `get_logger()` returns" (or
similar), matching the code's actual behavior.

---

_Reviewed: 2026-08-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
