"""EB-070 no-network guarantee, at import level.

`ambo.intake` reads local files only (the private drop is a filesystem path, never
a URL), which is why this rule carries no per-module exemption -- not even for
`intake/`.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# The HTTP client library EB-070 names (`requests`), plus the other common network
# clients a future contributor might reach for instead.
FORBIDDEN_NETWORK_IMPORT_NAMES: frozenset[str] = frozenset(
    {
        "requests",
        "httpx",
        "urllib3",
        "aiohttp",
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
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                names.add(node.module.split(".")[0])
    return names


def test_no_network_client_is_imported_anywhere(repo_root: Path) -> None:
    py_files = _iter_py_files(repo_root)
    assert py_files, (
        "No .py files scanned under src/ambo/, scripts/, or tests/ -- the scan "
        "itself is broken, not vacuously passing."
    )

    offenders: list[str] = []
    for py_file in py_files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        hits = _imported_top_level_names(tree) & FORBIDDEN_NETWORK_IMPORT_NAMES
        if hits:
            offenders.append(f"{py_file.relative_to(repo_root).as_posix()}: {sorted(hits)}")

    assert not offenders, "Network client import(s) found (EB-070 zero-network rule): " + "; ".join(
        offenders
    )
    print(f"no-requests guard: scanned {len(py_files)} file(s), 0 network-client imports.")


def test_strict_markers_rejects_an_unregistered_marker(tmp_path: Path) -> None:
    """`--strict-markers` is already active project-wide via `pyproject.toml`'s
    `addopts`; this plan registers no new marker. Proven here with a throwaway file
    run through a nested `pytest.main()`, never by adding an unregistered marker to
    the real suite."""
    scratch = tmp_path / "test_scratch_unregistered_marker.py"
    scratch.write_text(
        "import pytest\n\n"
        "@pytest.mark.definitely_not_a_registered_marker\n"
        "def test_noop() -> None:\n"
        "    assert True\n",
        encoding="utf-8",
    )

    result = pytest.main(["-q", "--strict-markers", "-p", "no:cacheprovider", str(scratch)])

    assert result != pytest.ExitCode.OK, (
        "An unregistered marker was accepted; --strict-markers should have rejected it."
    )
