"""Charter O-3 / EB-030 forbidden-dependency scope wall.

**Import-scoped, not tree-scoped** — a binding decision made at a human checkpoint
during plan 01-02 (recorded in `.planning/STATE.md`'s Decisions log and in
`01-02-SUMMARY.md`):

    "Charter O-3's forbidden-dependency rule is import-scoped, not tree-scoped. It
    governs what ambo's own code imports, NOT every transitive package name in the
    resolved dependency tree."

`scikit-learn` is present in `uv.lock`, arriving transitively via the
Charter-sanctioned `pymc-marketing` -> `pymc-extras` chain (`pymc-marketing` is
pinned by SPEC-08 section 3). A guard that parsed `uv.lock` for forbidden
distribution names would fail on this approved, already-reviewed dependency. This
module therefore asserts only against what `ambo`'s own code (plus `scripts/` and
`tests/`) actually imports — it does not parse `uv.lock`.
"""

from __future__ import annotations

import ast
from pathlib import Path

# Charter O-3 frameworks, by their *import* name -- not their distribution name,
# where the two differ (scikit-learn's distribution name is "scikit-learn"; its
# import name is "sklearn").
FORBIDDEN_IMPORT_NAMES: frozenset[str] = frozenset(
    {
        "robyn",
        "lightweight_mmm",
        "meridian",
        "prophet",
        "sklearn",
    }
)

_SCAN_DIRS = ("src/ambo", "scripts", "tests")


def _iter_py_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for rel in _SCAN_DIRS:
        base = repo_root / rel
        if base.is_dir():
            files.extend(base.rglob("*.py"))
    return files


def _imported_top_level_names(tree: ast.AST) -> set[str]:
    """The first dotted segment of every module a file imports.

    Comparing whole first-segments (not substring search) means a legitimate
    package whose name merely *contains* a forbidden name as a fragment never
    trips this guard, and an aliased import (`import sklearn as np`) is still
    caught because the alias name is never what's compared.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                names.add(node.module.split(".")[0])
    return names


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
