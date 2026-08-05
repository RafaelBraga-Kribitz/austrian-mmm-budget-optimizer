"""The fifth standing architectural guard (D-09): AD-030's mart-only rule.

Implements: AD-030, G-ARCH

Converts the AD-030 doorway rule -- `model`/`decide` reach data only through
`ambo.common.db`, `report` reaches data only through `exports/` -- from a one-time
grep verified once in Phase 3 into a standing check that fails the build the moment
Phase 4 (`model`), Phase 8 (`decide`), or Phase 9 (`report`) code reaches around it.

Same AST-walk idiom as `tests/unit/test_forbidden_deps.py` and
`tests/unit/test_import_independence.py` (Phase 1, T-010): offenders are collected
into a list rather than failing on first hit, one joined assertion message names
every offender found, and every scanning test prints a scan-count summary so a
future directory rename cannot quietly reduce this guard's coverage to zero without
anyone noticing.

`src/ambo/model/`, `src/ambo/decide/`, and `src/ambo/report/` do not exist yet --
their owning phases are 4, 8, and 9 -- so the first three tests below legitimately
scan zero files today. `test_guard_detects_a_known_offender` is the non-vacuity
proof: it exercises every detector helper against synthetic known-bad input written
to `tmp_path`, so this guard is trustworthy before it has anything real to scan.
"""

from __future__ import annotations

import ast
from pathlib import Path

# Direct data-read call names -- a pandas or duckdb literal read, never routed
# through ambo.common.db.
_FORBIDDEN_IO_CALL_NAMES: frozenset[str] = frozenset(
    {
        "read_csv",
        "read_parquet",
        "read_csv_auto",
        "read_json",
        "read_table",
    }
)

# Repository-relative path prefixes off-limits outside ambo.common.db. `exports/`
# is deliberately absent -- 03_MODULES section 10 grants src/ambo/report/ that
# access legitimately, and a repo-wide data-read ban would be wrong.
_FORBIDDEN_DATA_PATH_PREFIXES: frozenset[str] = frozenset(
    {
        "data/synthetic",
        "data/real_anon",
        "data/warehouse",
        "data/cache",
    }
)


def _py_files(base: Path) -> list[Path]:
    """Sorted `.py` files under `base`; an empty list when `base` does not exist
    (the owning package's phase has not landed yet -- not an error)."""
    if not base.is_dir():
        return []
    return sorted(base.rglob("*.py"))


def _forbidden_calls(tree: ast.AST) -> list[tuple[str, int]]:
    """(call_name, line) for every direct data-read call or `duckdb.connect` call
    found by walking `tree`'s `ast.Call` nodes."""
    offenders: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in _FORBIDDEN_IO_CALL_NAMES:
            offenders.append((func.id, node.lineno))
        elif isinstance(func, ast.Attribute):
            if func.attr in _FORBIDDEN_IO_CALL_NAMES:
                offenders.append((func.attr, node.lineno))
            elif (
                func.attr == "connect"
                and isinstance(func.value, ast.Name)
                and func.value.id == "duckdb"
            ):
                offenders.append(("duckdb.connect", node.lineno))
    return offenders


def _forbidden_path_literals(tree: ast.AST, prefixes: frozenset[str]) -> list[tuple[str, int]]:
    """(literal_value, line) for every string constant in `tree` that begins with
    one of `prefixes`, tolerating both forward-slash and backslash separators."""
    offenders: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        normalized = node.value.replace("\\", "/")
        if any(normalized.startswith(prefix) for prefix in prefixes):
            offenders.append((node.value, node.lineno))
    return offenders


def test_model_and_decide_never_read_data_files_directly(repo_root: Path) -> None:
    model_dir = repo_root / "src" / "ambo" / "model"
    decide_dir = repo_root / "src" / "ambo" / "decide"
    model_files = _py_files(model_dir)
    decide_files = _py_files(decide_dir)

    for base, files in ((model_dir, model_files), (decide_dir, decide_files)):
        assert files or not base.is_dir(), (
            f"{base} exists but the scan found zero .py files -- the scan itself is "
            "broken, not vacuously passing."
        )

    offenders: list[str] = []
    for py_file in [*model_files, *decide_files]:
        rel = py_file.relative_to(repo_root).as_posix()
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for name, line in _forbidden_calls(tree):
            offenders.append(f"{rel}:{line}: {name}")
        for value, line in _forbidden_path_literals(tree, _FORBIDDEN_DATA_PATH_PREFIXES):
            offenders.append(f"{rel}:{line}: {value!r}")

    assert not offenders, (
        "AD-030: model/ and decide/ code reaches data only through ambo.common.db, "
        "never a direct read call or a hardcoded data path -- offender(s): " + "; ".join(offenders)
    )
    print(
        f"mart-only guard (model/decide direct-read scan): scanned "
        f"{len(model_files) + len(decide_files)} file(s), 0 offenders."
    )


def test_only_db_module_opens_duckdb(repo_root: Path) -> None:
    src_root = repo_root / "src" / "ambo"
    allowed = src_root / "common" / "db.py"
    py_files = [p for p in _py_files(src_root) if p != allowed]

    assert py_files, "No .py files scanned under src/ambo/ -- the scan is broken."

    offenders: list[str] = []
    for py_file in py_files:
        rel = py_file.relative_to(repo_root).as_posix()
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for name, line in _forbidden_calls(tree):
            if name == "duckdb.connect":
                offenders.append(f"{rel}:{line}: {name}")
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] == "duckdb":
                        offenders.append(f"{rel}:{node.lineno}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] == "duckdb":
                    offenders.append(f"{rel}:{node.lineno}: from {node.module} import ...")

    assert not offenders, (
        "AD-030: src/ambo/common/db.py is the single permitted home for opening a "
        "duckdb connection or importing duckdb -- offender(s): " + "; ".join(offenders)
    )
    print(f"mart-only guard (duckdb confinement): scanned {len(py_files)} file(s), 0 offenders.")


def test_report_may_read_exports_but_no_other_data_directory(repo_root: Path) -> None:
    report_dir = repo_root / "src" / "ambo" / "report"
    report_files = _py_files(report_dir)

    assert report_files or not report_dir.is_dir(), (
        f"{report_dir} exists but the scan found zero .py files -- the scan itself "
        "is broken, not vacuously passing."
    )

    # exports/ is deliberately absent from _FORBIDDEN_DATA_PATH_PREFIXES: 03_MODULES
    # section 10 grants report/ that access legitimately, so a repo-wide data-read
    # ban that also caught exports/ would be wrong.
    offenders: list[str] = []
    for py_file in report_files:
        rel = py_file.relative_to(repo_root).as_posix()
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for value, line in _forbidden_path_literals(tree, _FORBIDDEN_DATA_PATH_PREFIXES):
            offenders.append(f"{rel}:{line}: {value!r}")

    assert not offenders, (
        "AD-030: report/ may read only exports/, never a data/synthetic, "
        "data/real_anon, data/warehouse, or data/cache path directly -- offender(s): "
        + "; ".join(offenders)
    )
    print(
        f"mart-only guard (report/ exports-only scan): scanned {len(report_files)} "
        "file(s), 0 offenders."
    )


def test_guard_detects_a_known_offender(tmp_path: Path) -> None:
    """The non-vacuity proof. `src/ambo/model/`, `src/ambo/decide/`, and
    `src/ambo/report/` don't exist yet, so the three tests above legitimately scan
    zero files. This test writes three synthetic offender modules and proves every
    detector helper fires on each -- a detector that finds nothing in known-bad
    input is broken, not passing."""
    csv_offender = tmp_path / "csv_offender.py"
    csv_offender.write_text(
        "import pandas as pd\n\ndf = pd.read_csv('somewhere.csv')\n",
        encoding="utf-8",
    )
    duckdb_offender = tmp_path / "duckdb_offender.py"
    duckdb_offender.write_text(
        "import duckdb\n\ncon = duckdb.connect('warehouse.duckdb')\n",
        encoding="utf-8",
    )
    path_offender = tmp_path / "path_offender.py"
    path_offender.write_text(
        "WAREHOUSE_PATH = 'data/warehouse/ambo.duckdb'\n",
        encoding="utf-8",
    )

    csv_tree = ast.parse(csv_offender.read_text(encoding="utf-8"), filename=str(csv_offender))
    duckdb_tree = ast.parse(
        duckdb_offender.read_text(encoding="utf-8"), filename=str(duckdb_offender)
    )
    path_tree = ast.parse(path_offender.read_text(encoding="utf-8"), filename=str(path_offender))

    csv_call_offenders = _forbidden_calls(csv_tree)
    duckdb_call_offenders = _forbidden_calls(duckdb_tree)
    path_literal_offenders = _forbidden_path_literals(path_tree, _FORBIDDEN_DATA_PATH_PREFIXES)

    assert csv_call_offenders, (
        "_forbidden_calls found no offender in a synthetic pandas read_csv() call -- "
        "a detector that finds nothing in known-bad input is broken, not passing."
    )
    assert duckdb_call_offenders, (
        "_forbidden_calls found no offender in a synthetic duckdb.connect() call -- "
        "a detector that finds nothing in known-bad input is broken, not passing."
    )
    assert path_literal_offenders, (
        "_forbidden_path_literals found no offender in a synthetic forbidden-prefixed "
        "string literal -- a detector that finds nothing in known-bad input is "
        "broken, not passing."
    )
    print(
        "mart-only guard non-vacuity proof: all three detector shapes (direct read "
        "call, duckdb.connect, forbidden data-path literal) fired against synthetic "
        "known-bad input written to tmp_path."
    )
