"""SIM-003 / W-2 simulate<->model import firewall, via AST walk (T-010).

An AST walk (not a runtime import) so a lazy import inside a function body is still
caught. Both `src/ambo/simulate/` and `src/ambo/model/` carry only their package
docstring `__init__.py` this phase -- the walk finds real files (the two
`__init__.py` stubs) but zero cross-package import statements, so the assertion
below is vacuously satisfied today, not skipped: it will start catching real
violations the moment either package grows a module that imports the other.

Also encodes the two remaining forbidden edges from `docs/MODULE_CONTRACTS.md`'s
dependency-directions table, since they are the same kind of fact:

- `pymc_marketing` imported nowhere outside `ambo/validate/crosscheck.py` (MD-003)
- the PyMC sampling entry point (`pm.sample()` / `pymc.sample()`) called nowhere
  outside `ambo/model/fit.py`

Both are vacuously true today (`crosscheck.py` and `fit.py` do not exist yet) and
become load-bearing in Phase 4.
"""

from __future__ import annotations

import ast
from pathlib import Path


def _py_files(base: Path) -> list[Path]:
    if not base.is_dir():
        return []
    return sorted(base.rglob("*.py"))


def _imported_module_paths(tree: ast.AST) -> set[str]:
    """Every module path a file imports, absolute or relative (dots preserved so a
    relative import is distinguishable from an absolute one of the same name)."""
    paths: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                paths.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * node.level
            paths.add(f"{prefix}{node.module or ''}")
    return paths


def _imports_package(module_path: str, package: str) -> bool:
    """True if `module_path` (as produced by `_imported_module_paths`) reaches into
    `ambo.<package>`, absolute or relative, exactly or as a sub-import."""
    if module_path in {f"ambo.{package}", f".{package}"}:
        return True
    return module_path.startswith(f"ambo.{package}.") or module_path.startswith(f".{package}.")


def test_simulate_and_model_do_not_import_each_other(repo_root: Path) -> None:
    simulate_files = _py_files(repo_root / "src" / "ambo" / "simulate")
    model_files = _py_files(repo_root / "src" / "ambo" / "model")
    scanned = len(simulate_files) + len(model_files)

    assert scanned > 0, (
        "No files found under src/ambo/simulate/ or src/ambo/model/ -- the scan is "
        "broken, not vacuously passing."
    )

    offenders: list[str] = []
    for py_file in simulate_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        rel = py_file.relative_to(repo_root).as_posix()
        for module_path in _imported_module_paths(tree):
            if _imports_package(module_path, "model"):
                offenders.append(f"{rel} imports {module_path}")
    for py_file in model_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        rel = py_file.relative_to(repo_root).as_posix()
        for module_path in _imported_module_paths(tree):
            if _imports_package(module_path, "simulate"):
                offenders.append(f"{rel} imports {module_path}")

    assert not offenders, (
        "simulate<->model cross-import found (SIM-003 / W-2 firewall): " + "; ".join(offenders)
    )
    print(
        f"import-independence guard: scanned {len(simulate_files)} simulate/ file(s) "
        f"and {len(model_files)} model/ file(s); 0 cross-imports (vacuously intact "
        "today -- both packages are otherwise empty, not skipped)."
    )


def test_pymc_marketing_imported_only_in_validate_crosscheck(repo_root: Path) -> None:
    src_root = repo_root / "src" / "ambo"
    allowed = src_root / "validate" / "crosscheck.py"

    py_files = sorted(src_root.rglob("*.py"))
    assert py_files, "No files found under src/ambo/ -- the scan is broken."

    offenders: list[str] = []
    for py_file in py_files:
        if py_file == allowed:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for module_path in _imported_module_paths(tree):
            root = module_path.lstrip(".").split(".")[0]
            if root == "pymc_marketing":
                offenders.append(py_file.relative_to(repo_root).as_posix())

    assert not offenders, (
        "pymc_marketing imported outside validate/crosscheck.py (MD-003): " + ", ".join(offenders)
    )
    print(
        f"pymc_marketing-confinement guard: scanned {len(py_files)} file(s) "
        "(vacuously true today -- validate/crosscheck.py does not exist yet)."
    )


def test_pymc_sample_called_only_in_model_fit(repo_root: Path) -> None:
    src_root = repo_root / "src" / "ambo"
    allowed = src_root / "model" / "fit.py"

    py_files = sorted(src_root.rglob("*.py"))
    assert py_files, "No files found under src/ambo/ -- the scan is broken."

    offenders: list[str] = []
    for py_file in py_files:
        if py_file == allowed:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "sample":
                continue
            callee = node.func.value
            if isinstance(callee, ast.Name) and callee.id in {"pm", "pymc"}:
                offenders.append(py_file.relative_to(repo_root).as_posix())

    assert not offenders, "pm.sample()/pymc.sample() called outside model/fit.py: " + ", ".join(
        offenders
    )
    print(
        f"pymc-sample-confinement guard: scanned {len(py_files)} file(s) "
        "(vacuously true today -- model/fit.py does not exist yet)."
    )
