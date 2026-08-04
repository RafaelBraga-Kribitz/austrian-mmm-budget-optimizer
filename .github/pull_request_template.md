<!--
This template carries only the [STD] merge-readiness items that a test cannot decide
(06_CHECKLISTS.md, D-24). The layout, ignore-rule, forbidden-dependency, import-independence,
and line-ending items are deliberately absent from this list — they are enforced by
`tests/unit/test_repo_layout.py`, `tests/unit/test_forbidden_deps.py`,
`tests/unit/test_import_independence.py`, `tests/unit/test_line_endings.py`, and
`tests/unit/test_gitignore.py` (plans 01-07/01-08), not by a box someone ticks. Do not
re-add them here — that would duplicate a machine-checked item (D-24).
-->

## Summary

<!-- What does this PR do, in one or two sentences? -->

## Checklist

- [ ] `docs/BUILD_LOG.md` entry appended for this milestone, with scope, decisions, and wall
      times
- [ ] Evidence attached — `make lint && make test` output pasted, and the CI run linked
- [ ] Effort budget respected — actual elapsed effort stated, and the strictly-greater-than-2×
      tripwire confirmed not tripped, or an ADR filed explaining why
- [ ] Every specification edit in this PR has its own ADR
- [ ] The numeric SSOT (`reports/NUMERIC_SSOT.md`) was regenerated in this PR if any reported
      number changed
- [ ] Review was performed against `07_QUALITY_STANDARDS.md` and `09_ANTI_PATTERNS.md`, with the
      reviewer stating "checked" explicitly
