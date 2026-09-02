# Phase 3: Warehouse - Pattern Map

**Mapped:** 2026-08-05
**Files analyzed:** 20 (new/modified)
**Analogs found:** 16 direct/role-match / 20; 4 no-analog (first dbt code in repo — conceptual precedent named)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `dbt/dbt_project.yml` | config | — | none (first dbt project) | no analog — conceptual precedent: `pyproject.toml` (project-level config, single home) |
| `dbt/profiles.yml` | config | — | none | no analog — conceptual precedent: `config/settings.yaml` (`paths.warehouse`) |
| `dbt/models/raw/raw_media_*.sql`, `raw_outcome_*.sql` | model (SQL, raw view) | file-I/O (CSV → typed view) | none in repo | no analog — conceptual precedent: `src/ambo/simulate/__main__.py`'s `_MEDIA_COLUMNS`/`_OUTCOME_COLUMNS` producing-side contract |
| `dbt/models/staging/stg_media_weekly.sql`, `stg_outcome_weekly.sql`, `stg_promo.sql`, `stg_calendar_weekly.sql` | model (SQL, transform) | transform (union + rename) | none | no analog — conceptual precedent: `platform_bias.py`'s column-order contract discipline |
| `dbt/models/marts/fct_mmm_input.sql`, `dim_layer.sql`, `fct_platform_reported.sql` + `_marts__schema.yml` | model (SQL, contract-enforced) | CRUD (build-time materialize) | none | no analog — RESEARCH.md Pattern 2/3 is the concrete external precedent (verified locally) |
| `dbt/models/tests/ad042_revenue_reconciliation.sql`, `channels_present_both_directions.sql` | test (dbt singular) | transform (SELECT returns rows on failure) | none | no analog — RESEARCH.md Pattern 4 |
| `src/ambo/common/db.py` | service / accessor | CRUD (read-only) | `src/ambo/common/config.py` | role-match (single-home settings/DB accessor idiom) |
| `src/ambo/common/errors.py` (add `DataContractError`) | utility (exception hierarchy) | — | `src/ambo/common/errors.py` itself | exact (extend in place) |
| `tests/unit/test_mart_only_access.py` | test (AST guard) | — | `tests/unit/test_forbidden_deps.py`, `tests/unit/test_import_independence.py` | exact (same idiom, extended scope) |
| `tests/unit/test_warehouse_build.py` | test (integration, subprocess) | request-response (invoke dbt, inspect returncode) | `tests/unit/test_repo_layout.py` (subprocess `git ls-files` idiom) | role-match |
| `tests/unit/test_db.py` | test (unit) | CRUD | none direct; nearest is any `tests/unit/test_*config*.py`-style fixture test | role-match (not read; see note) |
| `tests/unit/test_export_marts.py` | test (unit) | file-I/O | `src/ambo/simulate/__main__.py`'s `_atomic_write_csv`/`_write_media_csv` (byte-stable CSV writer under test) | role-match |
| `scripts/export_marts.py` | service (export script) | file-I/O (mart → CSV) | `src/ambo/simulate/__main__.py` (`_atomic_write_csv`, float_format, atomic write) | exact (byte-stable CSV writer pattern) |
| `Makefile` (`transform` target edit) | config | — | `Makefile` itself (existing `transform`/`test`/`lint` targets) | exact (extend in place) |
| `.github/workflows/ci.yml` (job 3 `dbt` edit + windows leg) | config (CI) | — | `.github/workflows/ci.yml`'s `test` job's `windows-latest` matrix + job 1's seed diff-check | exact (both precedents in same file) |
| `tests/fixtures/warehouse_poisoned/`, `tests/fixtures/real_anon_fake/` | fixture data | file-I/O | none | no analog — first fixtures dir; conceptual precedent: `data/synthetic/{s_a,s_b,s_c}/` shape |

## Pattern Assignments

### `tests/unit/test_mart_only_access.py` (test, AST guard — D-09, the 5th standing guard)

**Analog:** `tests/unit/test_forbidden_deps.py` and `tests/unit/test_import_independence.py`

**Imports pattern** (`test_forbidden_deps.py` lines 19-23):
```python
from __future__ import annotations

import ast
from pathlib import Path
```

**Scan-scope pattern** (`test_forbidden_deps.py` lines 37-46):
```python
_SCAN_DIRS = ("src/ambo", "scripts", "tests")


def _iter_py_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for rel in _SCAN_DIRS:
        base = repo_root / rel
        if base.is_dir():
            files.extend(base.rglob("*.py"))
    return files
```
For D-09, scope narrows to `src/ambo/model` and `src/ambo/decide` (forbidden CSV/parquet/duckdb) and `src/ambo/report` (forbidden anything outside `exports/`) — mirror `_py_files`/`_imported_module_paths` from `test_import_independence.py` (lines 27-44) rather than `test_forbidden_deps.py`'s flatter version, since D-09 needs both an AST-walk of `Call` nodes (for `read_csv`/`duckdb.connect`) *and* import-path walking (for `duckdb` module import outside `db.py`).

**Core AST-walk-for-forbidden-calls pattern** (`test_import_independence.py` lines 33-44, adapt `ast.Import`/`ast.ImportFrom` walk to also catch `ast.Call`):
```python
def _imported_module_paths(tree: ast.AST) -> set[str]:
    paths: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                paths.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * node.level
            paths.add(f"{prefix}{node.module or ''}")
    return paths
```
RESEARCH.md's Code Examples section already sketches the exact extension needed (`_FORBIDDEN_IO_CALLS = {"read_csv", "read_parquet", "read_csv_auto"}`, scanning `model`/`decide`, plus a `report/`-scoped string-literal scan for `data/synthetic`/`data/real_anon`/`data/warehouse`) — that sketch should be implemented in this exact idiom, not paraphrased.

**Assertion / failure-message pattern** (`test_forbidden_deps.py` lines 68-85, and `test_repo_layout.py` lines 81-95 for the "vacuous scan is broken, not passing" discipline):
```python
def test_no_forbidden_framework_is_imported_anywhere(repo_root: Path) -> None:
    py_files = _iter_py_files(repo_root)
    assert py_files, (
        "No .py files scanned under src/ambo/, scripts/, or tests/ -- the scan "
        "itself is broken, not vacuously passing."
    )
    offenders: list[str] = []
    for py_file in py_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        hit = _imported_top_level_names(tree) & FORBIDDEN_IMPORT_NAMES
        if hit:
            offenders.append(f"{py_file.relative_to(repo_root).as_posix()}: {sorted(hit)}")
    assert not offenders, "Forbidden framework import(s) found (Charter O-3): " + "; ".join(
        offenders
    )
    print(f"forbidden-deps guard: scanned {len(py_files)} file(s), 0 forbidden imports.")
```
Every guard test in this repo: (1) asserts the scan itself found files (never a silent vacuous pass), (2) collects offenders into a list rather than failing on first hit, (3) joins offenders into one assertion message, (4) prints a scan-count summary line at the end. D-09's new test must follow all four exactly — this is the house style, not incidental.

**`repo_root` fixture note:** every guard test signature takes `repo_root: Path` as a pytest fixture parameter (see all four analog functions above) — confirm/reuse the existing `conftest.py` fixture rather than re-deriving `repo_root()` inline (that helper already exists in `src/ambo/common/config.py` lines 45-55, but the test-level fixture is the one guard tests actually consume).

---

### `tests/unit/test_warehouse_build.py` (test, integration/subprocess — D-11, D-20, D-23)

**Analog:** `tests/unit/test_repo_layout.py` (subprocess idiom) + RESEARCH.md's directly-specified invocation

**Subprocess pattern** (`test_repo_layout.py` lines 70-78):
```python
def _tracked_files(repo_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]
```
For D-11's poisoned-fixture proof, mirror this exactly but with `check=False` (RESEARCH.md is explicit: `subprocess.run([...], check=False)`, then assert `returncode != 0`, and ideally grep captured stdout/stderr for the failing test's name so a red exit from an unrelated cause isn't mistaken for proof):
```python
result = subprocess.run(
    [
        "uv",
        "run",
        "dbt",
        "build",
        "--project-dir",
        "dbt",
        "--profiles-dir",
        "dbt",
        "--vars",
        '{"data_synthetic_path": "tests/fixtures/warehouse_poisoned"}',
    ],
    cwd=repo_root,
    check=False,
    capture_output=True,
    text=True,
)
assert result.returncode != 0
assert "unique" in result.stdout  # or the specific test node id
```

**D-23 path-assertion pattern** — combine `test_repo_layout.py`'s `git ls-files`-scan discipline with `src/ambo/common/config.py`'s `load_settings().paths.warehouse` accessor (lines 129-171, `load_settings()`):
```python
from ambo.common.config import load_settings

settings = load_settings()
assert settings.paths.warehouse.is_file()  # after `make transform` has run
```

**Vacuous-scan-is-broken discipline:** apply the same `assert py_files, "..."`-style guard from `test_repo_layout.py` line 83 (`assert tracked, "git ls-files returned nothing — the scan itself is broken."`) to any file-existence check in this test.

---

### `src/ambo/common/db.py` (service/accessor, CRUD read-only)

**Analog:** `src/ambo/common/config.py`

**Imports pattern** (`config.py` lines 17-28):
```python
from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from ambo.common.errors import ConfigError
```
`db.py` should mirror this shape: `import duckdb`, `import pandas as pd`, and `from ambo.common.config import load_settings` / `from ambo.common.errors import DataContractError` — resolving the warehouse path through `load_settings().paths.warehouse`, never hardcoded (per the explicit instruction in this phase's scope).

**`repo_root()`-independent path resolution pattern** (`config.py` lines 45-55):
```python
def repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise ConfigError(f"repo_root(): no pyproject.toml found in any parent directory of {current}")
```
`db.py`'s `connect()` should resolve `settings.paths.warehouse` (already anchored to `repo_root()` by `_resolve_paths_block`, `config.py` lines 118-126) — no independent path logic needed in `db.py` itself; this is exactly the "single home" discipline D-08 asks for, extended by example.

**Single-read / cache pattern** (`config.py` lines 129-131, `@functools.lru_cache`):
```python
@functools.lru_cache(maxsize=1)
def load_settings() -> Settings:
```
Consider whether `db.py`'s connection or contract-derived column set warrants the same caching discipline (D-08's "derive from yml" suggests a computed-once constant is idiomatic here too).

**Error-wrapping pattern** (`config.py` lines 162-171):
```python
try:
    return Settings(**data)
except ValidationError as exc:
    failing_keys = ", ".join(".".join(str(part) for part in error["loc"]) for error in exc.errors())
    raise ConfigError(
        f"load_settings(): invalid configuration in {settings_path} — failing "
        f"key path(s): {failing_keys}"
    ) from exc
```
`db.py`'s postcondition violations (D-10, collect-all-raise-once) should follow this `raise ... from exc`-when-wrapping / plain `raise DataContractError(...)`-when-original style. RESEARCH.md's Code Examples section already has a full `read_mmm_input()` skeleton in this exact idiom (collect `violations: list[str]`, single `raise DataContractError("\n".join(violations))` at the end) — implement that skeleton directly, it is not a paraphrase target.

---

### `src/ambo/common/errors.py` (add `DataContractError(AmboError)`)

**Analog:** `src/ambo/common/errors.py` itself (extend in place)

**Exact subclass pattern to follow** (lines 26-36):
```python
class ConfigError(AmboError):
    """Raised by `ambo.common.config` on invalid or missing configuration."""


class SimulationError(AmboError):
    """Raised by every module in `src/ambo/simulate/` (SPEC-01) for: a missing or
    invalid scenario YAML, an out-of-domain math input, a missing season-window row,
    and a failed decomposition audit. Inherits the redaction invariant above
    unchanged — a `SimulationError` message never contains private-drop content or
    path, exactly like every other `AmboError` subclass (no simulate-layer input is
    ever private, but the invariant is stated once on the root and holds for free)."""
```
`DataContractError` must be added as a third subclass in the same one-line-docstring-naming-the-raiser style, and must explicitly restate (or at minimum, satisfy) the root's no-private-content redaction invariant (`AmboError` docstring, lines 15-23) — even though warehouse data itself is Layer P (never private) today, D-20's fake Layer R fixture and Phase 6's eventual real data mean this invariant is worth a one-line acknowledgment in the new subclass's docstring, matching `SimulationError`'s own explicit restatement.

**Add a `docs/MODULE_CONTRACTS.md` entry in the same commit** — `test_repo_layout.py`'s `test_module_contracts_match_src_ambo_modules_exactly` (lines 129-161) will fail otherwise; this is a hard build-time consequence of touching `db.py`, not optional cleanup.

---

### `scripts/export_marts.py` (service, file-I/O — mart → committed CSV)

**Analog:** `src/ambo/simulate/__main__.py`'s CSV-writing helpers

**Atomic-write + byte-stable pattern** (`__main__.py` lines 74-99):
```python
def _atomic_write_csv(frame: pd.DataFrame, path: Path) -> None:
    tmp_path = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    try:
        with tmp_path.open("w", encoding="utf-8", newline="") as handle:
            frame.to_csv(
                handle,
                index=False,
                na_rep="",
                float_format="%.6f",
                lineterminator="\n",
            )
            handle.flush()
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise
```
This is the exact D-04 precedent (`%.6f` fixed float format) — `export_marts.py` should reuse this verbatim or import/share it, not reimplement float formatting independently. `lineterminator="\n"` + `newline=""` on open is what keeps the export LF-only and byte-stable under CI's diff-check (D-02), matching `.gitattributes`' LF pin (Phase 1 D-22) the same way `truth.json` and these CSVs already do.

**Column-order + dtype-cast-before-write pattern** (`__main__.py` lines 102-117):
```python
_MEDIA_COLUMNS: tuple[str, ...] = (
    "week_start",
    "channel",
    "spend_eur",
    "impressions",
    "platform_conversions",
    "platform_revenue_eur",
)


def _write_media_csv(media: pd.DataFrame, path: Path) -> None:
    frame = media.reindex(columns=list(_MEDIA_COLUMNS)).copy()
    frame["week_start"] = pd.to_datetime(frame["week_start"]).dt.strftime("%Y-%m-%d")
    frame["spend_eur"] = frame["spend_eur"].astype("Int64")
    ...
    _atomic_write_csv(frame, path)
```
`export_marts.py`'s registry-driven writer (D-03: grow-as-you-go dict) should follow this same `reindex(columns=...)` + explicit-dtype-cast-then-write shape per registry entry, so a later phase adding `allocation_scenarios.csv` or `attribution_gap.csv` extends the dict with a new `(columns, dtype-casts)` tuple rather than writing a new script.

**Header-comment precedent for D-05's a€ risk note:** `platform_bias.py` line 3's module docstring pattern (a one-line note naming the exact downstream concern) is the right shape for `export_marts.py`'s required header comment about the future Layer R a€ interaction.

---

### `Makefile` (`transform` target — D-21)

**Analog:** `Makefile` itself, existing `transform`/`simulate`/`test` targets

**Current stub-with-conditional to be replaced** (lines 82-92):
```makefile
DBT_PROJECT_FILE := dbt/dbt_project.yml

transform:
	@if [ -f $(DBT_PROJECT_FILE) ]; then \
		uv run dbt build --project-dir dbt; \
	else \
		echo "make transform: no dbt project at $(DBT_PROJECT_FILE) yet -- nothing to build. Expected until Phase 3. Check ran, found nothing to do."; \
	fi
```
D-21 replaces this whole block with the unconditional two-flag invocation. **Real-target precedent for the replacement's shape** (`simulate:`, lines 62-63 — a bare `uv run ...` line, no conditional, no echo):
```makefile
simulate:
	uv run python -m ambo.simulate all
```
New `transform` target should match this minimal shape:
```makefile
transform:
	uv run dbt build --project-dir dbt --profiles-dir dbt
```
Note the `--profiles-dir dbt` flag is mandatory per D-23/RESEARCH.md Pitfall 1 — omitting it changes path resolution behavior. Preserve the file's `SHELL := /bin/sh` / `.SHELLFLAGS := -eu -c` pin (lines 17-18) — do not touch it; it already makes any new recipe line portable.

**`.PHONY` list update:** `transform` is already declared at line 25 — no change needed there, but confirm no new target names are introduced (SPEC-08 §5's 18-target list is closed, per the file's own header comment lines 20-23).

---

### `.github/workflows/ci.yml` (job 3 `dbt` — D-22 Windows leg, D-02 diff-check)

**Analog (Windows matrix leg):** the existing `test` job (lines 57-98)

**Matrix + conditional-install pattern to copy verbatim:**
```yaml
  test:
    name: test
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - name: Install make (Windows only)
        if: runner.os == 'Windows'
        run: |
          choco install make -y
          make --version
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
          cache-dependency-glob: "uv.lock"
```
D-22 requires job 3 (`dbt`) to gain exactly this `strategy.matrix.os: [ubuntu-latest, windows-latest]` + the same `if: runner.os == 'Windows'` conditional `choco install make -y` step, keeping the job `name: dbt` unchanged (so it stays one of the six named jobs, matching how `test` stays one job despite two matrix legs).

**Analog (D-02 diff-check pattern):** job 1's season-windows seed diff-check (lines 44-50):
```yaml
      - name: Regenerate season-windows seed
        run: uv run python scripts/generate_season_windows.py
      - name: Fail on season-windows seed drift
        run: git diff --exit-code dbt/seeds/season_windows.csv
```
D-02's export diff-check must follow this exact two-step shape (regenerate, then `git diff --exit-code` on the specific path), added inside job 3 (`dbt`) after `make transform`:
```yaml
      - run: make transform
      - run: make export
      - name: Fail on export drift
        run: git diff --exit-code exports/
```

**Current job 3 body to extend** (lines 104-114):
```yaml
  dbt:
    name: dbt
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
          cache-dependency-glob: "uv.lock"
      - run: uv sync
      - run: make transform
```
`runs-on: ubuntu-latest` becomes `runs-on: ${{ matrix.os }}` under the new `strategy.matrix`, and the checkout step gains the Windows-only make-install step from the `test` job, positioned identically (right after checkout, before `setup-uv`).

---

### `tests/unit/test_export_marts.py` and `tests/unit/test_db.py` (unit tests)

**Analog:** `src/ambo/simulate/__main__.py`'s writer functions under test, plus the general pytest-fixture idiom used across `tests/unit/`. No existing test file exercises a CSV writer directly in this repo (Phase 2's simulator tests were not read in this pass — out of D-11/D-18 scope for pattern mapping, since RESEARCH.md's own Wave-0-gaps table already marks both files `❌ does not exist`), so treat `db.py`'s and `export_marts.py`'s own docstrings/skeletons (RESEARCH.md Code Examples) as the primary spec, and follow the four guard tests' assertion-collection + vacuous-scan discipline (see `test_mart_only_access.py` section above) for any AST- or filesystem-scanning sub-checks these two files also need (e.g., asserting the registry dict shape for D-03).

## Shared Patterns

### Guard-test idiom (AST walk, collect-all-offenders, vacuous-scan guard)
**Source:** `tests/unit/test_forbidden_deps.py`, `tests/unit/test_import_independence.py`, `tests/unit/test_repo_layout.py`
**Apply to:** `tests/unit/test_mart_only_access.py` (primary), any AST-scanning sub-check in `test_db.py`/`test_export_marts.py`
```python
assert py_files, "... the scan itself is broken, not vacuously passing."
offenders: list[str] = []
# ... collect ...
assert not offenders, "<rule name>: " + "; ".join(offenders)
print(f"<guard-name> guard: scanned {len(py_files)} file(s), 0 offenders.")
```

### Byte-stable, atomic, LF-only CSV write
**Source:** `src/ambo/simulate/__main__.py` lines 74-132 (`_atomic_write_csv`, `_write_media_csv`, `_write_outcome_csv`)
**Apply to:** `scripts/export_marts.py` (all registry entries)
```python
frame.to_csv(handle, index=False, na_rep="", float_format="%.6f", lineterminator="\n")
```
Plus the `.tmp-<pid>` / `os.replace` atomic-write wrapper and `newline=""` on file open.

### Settings-mediated path resolution (never hardcode a repo path)
**Source:** `src/ambo/common/config.py` (`repo_root()`, `PathsConfig`, `load_settings().paths.*`)
**Apply to:** `src/ambo/common/db.py` (`settings.paths.warehouse`), `scripts/export_marts.py` (`settings.paths.exports`), any test asserting a built artifact's location (`test_warehouse_build.py`)

### Typed exception hierarchy, one subclass per raising module, redaction invariant restated
**Source:** `src/ambo/common/errors.py`
**Apply to:** `DataContractError(AmboError)` in `errors.py`, raised from `db.py`

### `docs/MODULE_CONTRACTS.md` same-PR entry requirement (machine-enforced)
**Source:** `tests/unit/test_repo_layout.py::test_module_contracts_match_src_ambo_modules_exactly` (lines 129-161)
**Apply to:** `src/ambo/common/db.py` — a same-PR `docs/MODULE_CONTRACTS.md` entry is not optional; this guard test fails the build without it. `scripts/export_marts.py` is a `scripts/` file, outside this particular guard's `src/ambo/` scope, but CONTEXT.md's canonical_refs section explicitly names it as also needing a `MODULE_CONTRACTS.md` entry — verify whether a separate `scripts/`-scoped guard exists before assuming it doesn't apply.

### Makefile target style: bare `uv run ...`, no conditional once real
**Source:** `Makefile`'s `simulate:`/`validate-sim:` targets (lines 62-67)
**Apply to:** the new unconditional `transform:` target (D-21)

### CI job matrix + Windows make-install, without adding a job
**Source:** `.github/workflows/ci.yml`'s `test` job (lines 57-98)
**Apply to:** `dbt` job's new `windows-latest` leg (D-22)

### CI regenerate-then-diff-check drift gate
**Source:** `.github/workflows/ci.yml`'s `lint` job's season-windows steps (lines 44-50)
**Apply to:** `dbt` job's new export diff-check (D-02)

## No Analog Found

Files with no close match in the codebase — this is the first dbt code in the project, so all dbt-layer files are new territory. Named conceptual precedents (not literal analogs) below; the planner should treat RESEARCH.md's Pattern 1-5 / Code Examples sections as the primary source for these, since no repo file demonstrates the mechanism:

| File | Role | Data Flow | Reason | Nearest conceptual precedent |
|---|---|---|---|---|
| `dbt/dbt_project.yml` | config | — | first dbt project in repo | `pyproject.toml` — single project-level config home |
| `dbt/profiles.yml` | config | — | first dbt profile in repo | `config/settings.yaml`'s `paths.warehouse` — same path this profile must land on (D-23) |
| `dbt/models/raw/*.sql` | model | file-I/O | no dbt SQL exists yet | `src/ambo/simulate/__main__.py`'s `_MEDIA_COLUMNS`/`_OUTCOME_COLUMNS` — the exact producing-side column names/dtypes these raw models must read (see below) |
| `dbt/models/staging/*.sql`, `dbt/models/marts/*.sql` + schema ymls | model | transform / CRUD | no dbt SQL exists yet | RESEARCH.md Patterns 1-5 (empirically verified against the installed toolchain — treat as primary source, not a fallback) |
| `tests/fixtures/warehouse_poisoned/`, `tests/fixtures/real_anon_fake/` | fixture data | file-I/O | first `tests/fixtures/` directory | `data/synthetic/{s_a,s_b,s_c}/` — same column shape, deliberately poisoned/faked |

### Producing-side contract the raw dbt layer must read exactly (Phase 2 simulator writer, `src/ambo/simulate/__main__.py`)

```python
_MEDIA_COLUMNS: tuple[str, ...] = (
    "week_start",
    "channel",
    "spend_eur",
    "impressions",
    "platform_conversions",
    "platform_revenue_eur",
)
_OUTCOME_COLUMNS: tuple[str, ...] = ("week_start", "revenue_eur", "orders", "promo_flag")
```
Dtypes as written to CSV (lines 102-132): `week_start` is `YYYY-MM-DD` string; `spend_eur`, `impressions`, `platform_conversions`, `orders`, `promo_flag` are nullable `Int64` (render with no decimal point, empty string when NULL — an offline channel's NULL survives as empty, never `0`); `platform_revenue_eur` and `revenue_eur` are plain `float64` at `%.6f` fixed precision, empty string when NULL. `raw_media_p_sa.sql`/etc. must read these exact column names/types via `read_csv_auto` — RESEARCH.md's Pattern 1 code example already matches this column set correctly.

## Metadata

**Analog search scope:** `tests/unit/` (all `test_*.py`), `src/ambo/common/` (`config.py`, `errors.py`, `logging.py` not separately excerpted), `src/ambo/simulate/__main__.py`, `Makefile`, `.github/workflows/ci.yml`
**Files read in full:** `tests/unit/test_forbidden_deps.py`, `tests/unit/test_import_independence.py`, `tests/unit/test_repo_layout.py`, `src/ambo/common/config.py`, `src/ambo/common/errors.py`, `Makefile`, `.github/workflows/ci.yml`, `src/ambo/simulate/__main__.py` (targeted read, lines 1-154)
**Pattern extraction date:** 2026-08-05
