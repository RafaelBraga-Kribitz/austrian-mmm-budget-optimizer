"""Simulator and model must not import each other's transforms (SIM-003, T-3)."""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "ambo"


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            names.add(node.module.split(".")[0])
    return names


def test_synth_does_not_import_model_or_transforms():
    names = _imported_modules(SRC / "synth.py")
    assert "ambo.transforms" not in names
    assert "ambo.model" not in names
    assert "ambo.evaluate" not in names


def test_model_does_not_import_synth():
    names = _imported_modules(SRC / "model.py")
    assert "ambo.synth" not in names


def test_transforms_does_not_import_synth():
    names = _imported_modules(SRC / "transforms.py")
    assert "ambo.synth" not in names
