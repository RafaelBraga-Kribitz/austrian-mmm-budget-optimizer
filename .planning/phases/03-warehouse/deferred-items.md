# Deferred Items — Phase 3 (warehouse)

Out-of-scope discoveries logged per the executor's scope-boundary rule: not fixed,
not part of any Phase 3 plan's `files_modified`.

| Plan | Item | Detail |
|------|------|--------|
| 03-01 | Whole-repo `ruff format --check .` fails on 4 markdown files | `.planning/phases/02-ground-truth-simulator/02-PATTERNS.md`, `.planning/phases/02-ground-truth-simulator/02-RESEARCH.md`, `.planning/phases/03-warehouse/03-PATTERNS.md`, `.planning/phases/03-warehouse/03-RESEARCH.md` — ruff's markdown-embedded-code-fence formatter reformats fenced Python snippets inside these planning docs. Pre-existing for the 02-* pair (documented in `docs/BUILD_LOG.md`'s M1 close entry, 02-01); the 03-* pair is new in this session but neither file is in plan 03-01's `files_modified` and neither was touched by any of its three tasks. `ruff check .` and `uv run mypy` both pass cleanly repo-wide; `ruff format --check` scoped to `src tests scripts` (the actual Python surface) passes cleanly. Not fixed here — same precedent as 02-01. |
