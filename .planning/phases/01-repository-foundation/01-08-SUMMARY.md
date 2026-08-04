---
phase: 01-repository-foundation
plan: 08
subsystem: infra
tags: [leak-scan, pre-commit, ruff, nbstripout, detect-private-key, governance]

# Dependency graph
requires:
  - phase: 01-04
    provides: "src/ambo/common/config.py -- load_settings(), private_drop -- the single AMBO_PRIVATE_DROP resolution path the scanner reuses"
  - phase: 01-05
    provides: "Makefile's lint target (ruff check / ruff format --check / mypy) that .pre-commit-config.yaml's ruff hooks stay consistent with"
provides:
  - "scripts/leak_scan.py -- the leak scanner: three modes (pattern subset, --full, --staged), three pattern classes (private_drop, contact, currency_literal), exit codes 0/1/2, a Finding record that structurally cannot carry matched text"
  - "tests/unit/test_leak_scan.py -- 13 tests proving all three modes, both scoping directions, the .env.example carve-out, and the never-echo-the-match contract, all on synthetic fixtures inside tmp_repo"
  - ".pre-commit-config.yaml -- the seven EB-002 hooks (ruff-check, ruff-format, end-of-file-fixer, check-yaml, detect-private-key, nbstripout, local leak-scan), every non-local repo pinned to a released tag"
  - "Fake-key probe evidence (detect-private-key blocks a synthetic RSA key on a scratch branch, zero commits ever made on it) -- for 01-09 to fold into the consolidated BUILD_LOG M0 entry"
affects: [01-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dynamic-vs-static pattern split for the private-drop class: the literal AMBO_PRIVATE_DROP value is resolved fresh at scan time via load_settings() (so a test that sets the env var and clears the cache genuinely changes what is scanned for), while the generic Windows/POSIX-path-adjacent shape is a module-level compiled constant (import-time, per the <10s budget) -- both share the 'private_drop' finding class name"
    - "Assignment-operator requirement on the generic private-drop shape (AMBO_PRIVATE_DROP[:=]<path>, not bare adjacency) -- excludes the project's own shell-interpolation documentation style ($AMBO_PRIVATE_DROP/staged/) which is a relative continuation, not a leaked value"
    - ".env.example carve-out: the generic-shape check excludes exactly this one file (01-02's sanctioned fictional AMBO_PRIVATE_DROP=<path> line); the dynamic literal-value check still covers it, so a real value pasted there by mistake is still caught"
    - "Finding as typing.NamedTuple with exactly four fields (path, line, pattern_class, match_hash) -- no field can hold matched text, a structural guarantee rather than a formatting convention"
    - "argparse subclassed to raise a local exception from .error() instead of calling sys.exit directly, so main(argv) stays a pure argv -> int function with a single process-exit call site at the __main__ guard"
    - "git ls-files enumeration + raw-bytes NUL-byte binary check (git's own heuristic) before UTF-8 decode, one read per file"

key-files:
  created:
    - scripts/leak_scan.py
    - tests/unit/test_leak_scan.py
    - .pre-commit-config.yaml
  modified:
    - .planning/phases/01-repository-foundation/01-08-PLAN.md

key-decisions:
  - "PRIVATE_DROP_PATTERNS (the module constant) holds only the generic assignment-shape regex, compiled once at import; the literal resolved-path check is a separate, call-time-resolved needle list -- both are exposed under the same 'private_drop' finding-class name so the plan's exports list (PRIVATE_DROP_PATTERNS, scan_tree, scan_staged, main, Finding, CONTACT_PATTERNS, CURRENCY_LITERAL_PATTERN, CONTACT_SCAN_ROOTS) is satisfied literally while keeping the dynamic behavior tests require (env var set + cache clear must change what is found)."
  - ".env.example is excluded from the generic private-drop shape check only. Without this carve-out the scanner would flag its own repository's sanctioned example line (AMBO_PRIVATE_DROP=<fictional path>, authored in 01-02) and 'uv run python scripts/leak_scan.py exits 0 on the clean repository' would be unsatisfiable. The dynamic literal-value check is NOT exempted, so a real value accidentally pasted there is still caught."
  - "Phone pattern requires an Austrian international (+43/0043) or national (leading 0) prefix followed by 2-4 more digit groups, not any long digit run -- verified against decimal spend figures (0.75, 123456.78) to confirm none match."
  - "Assignment-operator proximity ([:=] directly after AMBO_PRIVATE_DROP, not bare \\W{0,n} adjacency) for the generic shape class -- a plain-adjacency version false-positived on this repository's own $AMBO_PRIVATE_DROP/staged/ and $AMBO_PRIVATE_DROP/blocklist.txt documentation lines (SPEC-02, .planning/intel/constraints.md), which are shell-interpolation references, not leaked values."
  - "ruff-pre-commit pinned to v0.16.1 (exact match to the pinned ruff dev dependency version); nbstripout pinned to 0.9.1 (exact match to the pinned nbstripout dev dependency version); pre-commit-hooks pinned to v6.0.0 (latest released tag at authoring time). All three verified against the actual upstream repository tags, not guessed."
  - "mypy is not a pre-commit hook (matches T-007/EB-002: seven hooks, not eight) -- make lint already runs it and CI job 1 runs make lint."

requirements-completed: [REQ-scope-out, REQ-dl8-quality]

coverage:
  - id: D1
    description: "scripts/leak_scan.py implements three modes (pattern subset, --full, --staged) and three pattern classes (private_drop, contact, currency_literal), with exit codes 0/1/2"
    requirement: "REQ-dl8-quality"
    verification:
      - kind: unit
        ref: "tests/unit/test_leak_scan.py#test_exit_codes_clean_finding_and_usage_error"
        status: pass
      - kind: other
        ref: "uv run python scripts/leak_scan.py (exit 0, <10s); --bogus-flag (exit 2, stderr usage); --full with AMBO_PRIVATE_DROP unset (exit 0, blocklist-unavailable notice on stderr)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Contact and currency-literal pattern classes are path-scoped in both directions (found in scope, ignored out of scope), and Finding never carries matched text on either output stream"
    requirement: "REQ-scope-out"
    verification:
      - kind: unit
        ref: "tests/unit/test_leak_scan.py#test_contact_email_found_under_data_real_anon, #test_contact_email_ignored_outside_scoped_roots, #test_currency_literal_found_in_notebook, #test_currency_literal_ignored_outside_notebooks, #test_output_never_contains_the_planted_value_on_either_stream"
        status: pass
    human_judgment: false
  - id: D3
    description: ".pre-commit-config.yaml declares exactly the seven EB-002 hooks with pinned revisions; pre-commit run --all-files and make lint are both green"
    requirement: "REQ-dl8-quality"
    verification:
      - kind: other
        ref: "grep -c '^\\s*-\\s*id:' .pre-commit-config.yaml == 7; grep -c 'rev:' == 3; uv run pre-commit run --all-files exit 0; make lint exit 0; make lint exits non-zero on a deliberately introduced ruff violation, reverted via git checkout -- scripts/leak_scan.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "detect-private-key blocks a staged synthetic RSA key before any commit object exists, on a scratch branch deleted afterward with zero commits ever made on it"
    requirement: "REQ-dl8-quality"
    verification:
      - kind: other
        ref: "scratch-01-08-fake-key-probe: git commit exit 1, 'Private key found: docs/_scratch_fake_key_probe.pem', git log unchanged (0d12366), branch deleted via git branch -d (fast-forward, no unique commits)"
        status: pass
    human_judgment: false

duration: ~30min
completed: 2026-08-04
status: complete
---

# Phase 1 Plan 8: Leak Scanner and Pre-Commit Toolchain Summary

**`scripts/leak_scan.py` (three modes, three path-scoped pattern classes, hash-only findings), 13 synthetic-fixture tests proving both scoping directions, and `.pre-commit-config.yaml` wiring the seven EB-002 hooks with pinned revisions -- proven by a fake-key probe that blocks before any commit object exists.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-08-04T22:00:00+02:00 (approx.)
- **Completed:** 2026-08-04T22:30:00+02:00 (approx.)
- **Tasks:** 3 (all `type="auto"`, no checkpoints)
- **Files modified:** 3 created (`scripts/leak_scan.py`, `tests/unit/test_leak_scan.py`, `.pre-commit-config.yaml`) + 1 pre-existing file touched by `end-of-file-fixer` (`01-08-PLAN.md`, missing trailing newline)

## Accomplishments

- `scripts/leak_scan.py`: three pattern classes exactly as D-26 scopes them --
  `PRIVATE_DROP_PATTERNS` (whole tree; a dynamic literal-value check resolved fresh
  through `load_settings().private_drop` on every call, plus a static generic
  assignment-shape regex requiring `AMBO_PRIVATE_DROP[:=]<path>`), `CONTACT_PATTERNS`
  (email/URL/Austrian-phone shapes, scoped to `data/real_anon/` and
  `reports/ingestion/` only), `CURRENCY_LITERAL_PATTERN` (scoped to `*.ipynb` only).
  Three modes: the pattern subset (default), `--full` (subset plus
  `$AMBO_PRIVATE_DROP/blocklist.txt`, skipped gracefully with a notice when the drop
  or the file is absent), `--staged` (`git diff --cached -U0` only). Exit codes
  0/1/2. `Finding` is a `typing.NamedTuple` with exactly `(path, line, pattern_class,
  match_hash)` -- no field can hold matched text.
- Discovered and fixed two false-positive sources against this repository's own
  tracked files before Task 1 was done: (a) the project's own
  `$AMBO_PRIVATE_DROP/staged/` and `$AMBO_PRIVATE_DROP/blocklist.txt`
  shell-interpolation documentation lines (SPEC-02, `.planning/intel/constraints.md`)
  matched a bare-adjacency version of the generic private-drop shape -- fixed by
  requiring an explicit `[:=]` assignment operator; (b) `.env.example`'s own
  sanctioned fictional `AMBO_PRIVATE_DROP=<path>` line (authored in plan 01-02)
  matched the same generic shape -- fixed by excluding exactly that one file from
  the generic-shape check (the dynamic literal-value check still covers it). Both
  fixes were necessary for the plan's own acceptance criterion ("exits 0 on the
  clean repository") to be satisfiable at all.
- `tests/unit/test_leak_scan.py`: 13 tests, all synthetic (`.invalid`-domain email,
  fictional Austrian phone shape proven in a manual regex check, fictional currency
  figure, fictional drop path, fictional blocklist token) -- contact class proven in
  both scoping directions, currency-literal class proven in both scoping directions,
  private-drop literal path proven via a cleared `load_settings` cache, the
  `.env.example` carve-out proven not to suppress the literal check, the
  never-echo-the-match contract proven on both `stdout` and `stderr` via `capsys`,
  full mode proven with a blocklist present and absent, staged mode proven to find a
  staged value and ignore an unstaged one, and all three exit codes.
- `.pre-commit-config.yaml`: exactly seven hooks -- `ruff-check` + `ruff-format`
  (`astral-sh/ruff-pre-commit` `v0.16.1`, matching the pinned `ruff` dev dependency
  exactly), `end-of-file-fixer` / `check-yaml` / `detect-private-key`
  (`pre-commit/pre-commit-hooks` `v6.0.0`), `nbstripout` (`kynan/nbstripout` `0.9.1`,
  matching the pinned dev dependency exactly), and the local `leak-scan` hook
  (`scripts/leak_scan.py --staged`, `pass_filenames: false`, `always_run: true`).
  Every non-local `rev` verified against the real upstream tag list before pinning.
  `uv run pre-commit run --all-files` is green; the only pre-existing file it
  rewrote was `01-08-PLAN.md`'s missing trailing newline (`end-of-file-fixer`).
  `make lint` is green and was proven to fail on a deliberately introduced `ruff`
  violation (an unused `import os,sys` line), then cleanly reverted via
  `git checkout -- scripts/leak_scan.py`.
- **Fake-key probe** (WBS T-007 validation, D-29-style manual-only evidence): on
  scratch branch `scratch-01-08-fake-key-probe`, staged
  `docs/_scratch_fake_key_probe.pem` containing a synthetic (never-real) PEM-style
  RSA-private-key BEGIN/END marker block, attempted `git commit`. The
  `detect-private-key` hook blocked it: exit code 1, message
  `Private key found: docs/_scratch_fake_key_probe.pem`. `git log --oneline -1`
  before and after the attempt shows the same commit (`0d12366`) -- no commit
  object was ever created. The probe file was unstaged and deleted, `m0-bootstrap`
  checked back out, and the scratch branch deleted with a plain (non-force)
  `git branch -d`, which succeeded because the branch carried zero unique commits.
  `git branch --list` afterward shows exactly `m0-bootstrap` and `main`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement the leak scanner with its three modes and three pattern classes** - `868afa9` (feat)
2. **Task 2: Prove all three modes and all three pattern classes with synthetic fixtures** - `0d12366` (test)
3. **Task 3: Wire the pre-commit toolchain and prove the fake-key probe blocks** - `dc6ddfa` (feat)

**Plan metadata:** committed separately after this summary is written.

## Files Created/Modified

- `scripts/leak_scan.py` - The leak scanner: three pattern classes, three modes, exit codes 0/1/2, `Finding` NamedTuple
- `tests/unit/test_leak_scan.py` - 13 tests covering all three modes, both scoping directions, the `.env.example` carve-out, and the redaction contract
- `.pre-commit-config.yaml` - The seven EB-002 hooks, all non-local `repo` entries pinned to a verified released tag
- `.planning/phases/01-repository-foundation/01-08-PLAN.md` - Trailing-newline fix from `end-of-file-fixer` during `pre-commit run --all-files`

## Decisions Made

See `key-decisions` in the frontmatter for the full list. The two load-bearing ones:
excluding `.env.example` from the private-drop generic-shape check (without it, the
scanner cannot pass on its own repository), and requiring an explicit `[:=]`
assignment operator rather than bare adjacency for that same check (without it, the
project's own `$AMBO_PRIVATE_DROP/staged/`-style documentation lines false-positive).
Both were necessary for the plan's own stated acceptance criteria to be satisfiable,
not scope changes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Generic private-drop pattern false-positived on this repository's own shell-interpolation documentation**
- **Found during:** Task 1, first run of `uv run python scripts/leak_scan.py` against the real tree
- **Issue:** A bare-adjacency version of the generic `AMBO_PRIVATE_DROP`-adjacent-path regex matched `$AMBO_PRIVATE_DROP/staged/` and `$AMBO_PRIVATE_DROP/blocklist.txt` in `docs/SPEC-02_agency_data_pipeline.md` and `.planning/intel/constraints.md` -- legitimate shell-interpolation documentation, not a leaked value, which would have made the "exits 0 on the clean repository" acceptance criterion fail.
- **Fix:** Tightened the regex to require an explicit `[:=]` assignment operator directly after the env var name, which matches `AMBO_PRIVATE_DROP=<path>` / `AMBO_PRIVATE_DROP: <path>` forms but not a bare `$AMBO_PRIVATE_DROP/<continuation>` reference.
- **Files modified:** `scripts/leak_scan.py`
- **Verification:** `uv run python scripts/leak_scan.py` exits 0 with no findings on the clean tree
- **Committed in:** `868afa9` (Task 1 commit)

**2. [Rule 1 - Bug] Generic private-drop pattern false-positived on `.env.example`'s own sanctioned example line**
- **Found during:** Task 1, same first-run check, after fixing deviation 1
- **Issue:** After the assignment-operator fix, the scanner still flagged `.env.example`'s `AMBO_PRIVATE_DROP=<fictional path>` line (authored in plan 01-02, `01-02-PLAN.md`'s explicit instruction) -- the exact shape the generic class is designed to catch, but this file's occurrence is the one sanctioned, reviewed example, not a leak.
- **Fix:** Added a scope predicate (`_not_env_example`) excluding exactly `.env.example` from the generic-shape pattern class. The dynamic literal-value check (matching the actual resolved `AMBO_PRIVATE_DROP` env value) is deliberately NOT exempted, so a real value pasted there by mistake is still caught -- proven by `test_env_example_carve_out_does_not_suppress_the_literal_check`.
- **Files modified:** `scripts/leak_scan.py`
- **Verification:** `uv run python scripts/leak_scan.py` exits 0 on the clean tree; the new test proves the literal check still fires on `.env.example`
- **Committed in:** `868afa9` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 -- bugs in the initial pattern design that made the plan's own acceptance criteria unsatisfiable against the real repository, found and fixed before Task 1's commit).
**Impact on plan:** No scope creep. Both fixes were required for "exits 0 on the clean repository" to hold; both are documented in the module docstring itself as permanent scope statements, not workarounds.

## Issues Encountered

`ruff format` initially disagreed with a manual line-break I introduced to fix an
`E501` line-too-long violation in `_scan_single_line` -- resolved by running
`uv run ruff format scripts/leak_scan.py` directly rather than hand-formatting, which
produced the canonical layout both `ruff check` and `ruff format --check` agree on.
Not tracked as a formal deviation (tooling formatting, no logic change).

## User Setup Required

None - no external service configuration required. `uv run pre-commit install` was
run as part of Task 3's own verification (this is also what `make setup` runs).

## Next Phase Readiness

- The leak scanner is live in three places going forward, exactly as T-01-02's threat
  mitigation describes: the staged-mode pre-commit hook (already installed, blocks
  before any commit object exists), CI job 6 (pattern-subset mode, to be wired in
  01-09), and full mode (local-only, for a developer with `AMBO_PRIVATE_DROP` set).
- `.pre-commit-config.yaml` and `scripts/leak_scan.py` are the last of the four
  governance showpieces GB section 8 names (alongside `check_layer_order.py`,
  `check_ssot_consistency.py`, and the ADR discipline already in place from
  plan 01-03) -- 01-09 is free to wire CI job 6 against `scripts/leak_scan.py`
  directly (no `--staged`, no `--full`: the plain pattern-subset default) with no
  further scanner changes needed.
- The fake-key probe evidence above (hook name `detect-private-key`, blocked message,
  scratch branch name, zero commits) is ready for 01-09's consolidated
  `docs/BUILD_LOG.md` M0 entry to cite verbatim, per this plan's own action text.
- `make setup`'s `uv run pre-commit install` line (already present from plan 01-05)
  now has a real `.pre-commit-config.yaml` to install against -- a fresh clone's
  `make setup` is fully functional for the first time in this phase.

---
*Phase: 01-repository-foundation*
*Completed: 2026-08-04*

## Self-Check: PASSED

All 4 artifacts found on disk (`scripts/leak_scan.py`, `tests/unit/test_leak_scan.py`,
`.pre-commit-config.yaml`, this SUMMARY.md); all 4 commits verified present in git
history (`868afa9`, `0d12366`, `dc6ddfa`, `9e4fb5b`).
