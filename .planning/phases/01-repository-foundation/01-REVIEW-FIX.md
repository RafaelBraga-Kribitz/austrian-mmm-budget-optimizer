---
phase: 01-repository-foundation
fixed_at: 2026-08-04T22:25:59Z
review_path: .planning/phases/01-repository-foundation/01-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 1: Code Review Fix Report

**Fixed at:** 2026-08-04T22:25:59Z
**Source review:** .planning/phases/01-repository-foundation/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (fix_scope: critical_warning -- CR-01, CR-02, WR-01, WR-02, WR-03, WR-04; IN-01 excluded)
- Fixed: 6
- Skipped: 0

## Fixed Issues

### CR-01: `.env.example` leak-scan carve-out is a real, exploitable blind spot in CI

**Files modified:** `scripts/leak_scan.py`, `tests/unit/test_leak_scan.py`
**Commit:** `8643761`
**Applied fix:** Adapted the review's suggested `<abs-path>`-bracket placeholder check to
the file's actual convention (a literal fictional Windows path, not a bracketed
placeholder). The generic-shape check no longer exempts `.env.example` outright; it
now captures the assigned value via a named regex group and, for that one file,
compares it case-insensitively against a pinned constant
(`_ENV_EXAMPLE_PLACEHOLDER_VALUE`, matching the exact fictional value the real
`.env.example` documents). Anything else assigned there -- in particular a real
absolute path pasted by mistake -- is flagged like any other file, even when
`AMBO_PRIVATE_DROP` is unset in CI (the actual CI condition, previously a silent
no-op). Updated `test_env_example_carve_out_does_not_suppress_the_literal_check`'s
assertion (now 2 findings instead of 1, since both checks fire) and added
`test_env_example_real_path_caught_by_shape_check_even_when_env_var_unset` and
`test_env_example_documented_placeholder_is_not_flagged` to prove the exact gap
described in CR-01 is closed. Verified: full 15-test `test_leak_scan.py` suite
passes; a full-tree `leak_scan.py` run over the real worktree (including its own
new comments and the real `.env.example`) is clean; ruff check/format and a direct
functional probe (real path in `.env.example` -> 1 finding; documented placeholder
-> 0 findings) confirmed the fix and caught two self-match regressions (in a
doc-comment example and in the added test's own literal) before commit, both fixed
by using `<abs-path>`-style placeholders / referencing the module constant instead
of inlining the literal.

### CR-02: `PrivatePathFilter` does not redact exception tracebacks or non-`str` log values

**Files modified:** `src/ambo/common/logging.py`, `tests/unit/test_logging.py`
**Commit:** `fb5edb8`
**Applied fix:** Adapted the review's placeholder code sample into a working
implementation. `_redact` now stringifies a non-`str` `msg`/arg before matching,
but only returns the redacted *string* when a needle actually matched; when no
needle matches, it returns the *original* value unchanged, so a non-str arg used
with a non-`%s` conversion (e.g. `%d` on an int) still formats correctly downstream
-- a regression the review's own placeholder snippet would have introduced. When
`record.exc_info` is set, the traceback is rendered via
`logging.Formatter().formatException(...)` (or reused if already cached), redacted,
and cached onto `record.exc_text` before the standard `Formatter.format()` call
reuses it. Added `test_redaction_in_exception_traceback` (proves `logger.exception(...)`
no longer leaks the real path via its traceback), `test_redaction_of_non_str_msg`
(proves a `Path` passed directly as `msg` is redacted), and
`test_non_str_arg_without_the_private_path_is_not_corrupted` (proves the
type-preservation fallback prevents a `%d`-formatting regression). Verified: full
10-test `test_logging.py` suite passes, ruff check/format and mypy pass on both
files, and a full-tree leak scan is clean. Note: initial test runs under plain
`python -m pytest` falsely failed because that interpreter resolved to the main
repository's `.venv` (a stale install), not the worktree's own build; switching to
`uv run --project .` inside the worktree confirmed the fix is correct.

### WR-01: SSOT unit-symbol normalization is asymmetric -- `×` vs `x` never cross-match

**Files modified:** `scripts/check_ssot_consistency.py`, `tests/unit/test_governance_checks.py`
**Commit:** `47cf4e5`
**Applied fix:** Applied the review's suggested fix directly: extracted a shared
`_normalize_unit` helper and applied it to both the literal's unit and the SSOT
row's own unit (previously only the literal side was normalized). Added
`test_matches_any_row_reconciles_multiplier_symbol_across_x_and_times` and its
mirror in the other direction. Verified: `test_governance_checks.py` passes (16
tests), ruff/mypy clean (pre-existing `import-untyped`/`unused-ignore` mypy noise
confirmed present before this change too, via a diff against the original file).

### WR-02: SSOT literal parsing assumes period-decimal formatting; Austrian comma-decimal input silently fails to match

**Files modified:** `scripts/check_ssot_consistency.py`, `tests/unit/test_governance_checks.py`
**Commit:** `47cf4e5` (same commit as WR-01, same function)
**Applied fix:** The review offered two options (pin a canonical format with
explicit rejection, or locale-aware parsing); implemented the cheaper option (a).
Added `_reject_if_ambiguous_decimal_comma`, which raises `SsotError` when a value
ends in a comma followed by exactly one or two digits -- never a valid
thousands-grouping comma under this parser's convention (a genuine thousands group
is always exactly three digits), and always the shape of either a bare decimal
comma (`234,56`, which the old code silently misparsed to the wrong magnitude via
comma-stripping) or the trailing half of an Austrian-formatted literal (`1.234,56`,
which the old code's `float()` call raised on internally and silently treated as
"no match"). Applied to both the document literal and the SSOT row's own value.
Added four regression tests covering both ambiguous shapes (bare comma, Austrian
period-thousands) on both sides (literal and row), plus a control test proving a
genuine well-formed thousands comma (`1,234.56`) still reconciles. Verified:
`test_governance_checks.py` passes; `SsotError` propagates correctly up through
`_reconcile` into `main()`'s existing exception handling (exit code 1), matching
the module's existing "malformed input is an error, not a silent skip" contract.

### WR-03: `check_layer_order.py` crashes uncaught on a root-commit edge case instead of reporting a clean exit code

**Files modified:** `scripts/check_layer_order.py`, `tests/unit/test_governance_checks.py`
**Commit:** `688b19a`
**Applied fix:** Applied the review's suggested fix directly: `_diff_is_append_only`
now checks for a parent commit via `git rev-parse --verify -q {commit}^` before
diffing, and diffs against git's well-known empty-tree object
(`4b825dc642cb6eb9a060e54bf8d69288fbee4904`) when there is none, treating a root
commit's own change as a full (trivially append-only) addition instead of letting
`subprocess.CalledProcessError` propagate uncaught. Added
`test_diff_is_append_only_handles_the_repository_root_commit`, which calls the
function directly against a real single-commit throwaway repo. Verified: the new
test fails with the exact `CalledProcessError` the review describes when run
against the pre-fix version of the file (confirmed via a temporary diff-and-revert
against the committed original), and passes against the fixed version; full
16-test `test_governance_checks.py` suite passes; ruff/mypy clean (same
pre-existing mypy import-untyped noise as WR-01/02, confirmed unrelated to this
change).

### WR-04: `test_set_private_drop_resolves_to_a_path` does not actually exercise absolute-path resolution on POSIX

**Files modified:** `tests/unit/test_config.py`
**Commit:** `7de8cb5`
**Applied fix:** Applied the review's suggested fix directly: added the same
`sys.platform`-branched `FAKE_PRIVATE_DROP` fixture pattern already used in
`test_leak_scan.py` and `test_logging.py`, replacing the hardcoded `D:/...` literal,
and added an explicit `is_absolute()` assertion so the test's name matches what it
proves on both platforms. Verified: full 9-test `test_config.py` suite passes;
ruff/mypy clean (same pre-existing import-untyped mypy noise, unrelated to this
change).

## Skipped Issues

None -- all 6 in-scope findings (CR-01, CR-02, WR-01, WR-02, WR-03, WR-04) were
fixed and verified. IN-01 (`MODULE_CONTRACTS.md` wording) was out of scope for this
run (`fix_scope: critical_warning`).

---

_Fixed: 2026-08-04T22:25:59Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
