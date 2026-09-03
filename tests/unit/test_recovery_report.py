"""Tests for the generated RECOVERY_REPORT (T-406 / VR-703).

Implements: VR-703
"""

from __future__ import annotations

import ast
from pathlib import Path

from ambo.common.config import repo_root
from ambo.validate.report import (
    _CLOSING_MIN_CHARS,
    CLOSING_TEMPLATE,
    SECTION_HEADINGS,
    generate_recovery_report,
    section_headings_in,
)


def test_closing_template_meets_spec() -> None:
    assert len(CLOSING_TEMPLATE) >= _CLOSING_MIN_CHARS
    lower = CLOSING_TEMPLATE.lower()
    assert "md-020" in lower
    assert "lift test" in lower


def test_section_headings_are_spec_05_section_8() -> None:
    assert SECTION_HEADINGS[0] == "## Verdict"
    assert SECTION_HEADINGS[-1] == "## What this does and does not prove"
    assert len(SECTION_HEADINGS) == 8


def test_report_source_does_not_sample() -> None:
    source = (repo_root() / "src/ambo/validate/report.py").read_text(encoding="utf-8")
    assert "sample_model" not in source
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "sample":
            continue
        callee = node.func.value
        if isinstance(callee, ast.Name) and callee.id in {"pm", "pymc"}:
            raise AssertionError("pm.sample in report.py (VR-703)")


def test_makefile_recover_is_not_a_stub() -> None:
    text = (repo_root() / "Makefile").read_text(encoding="utf-8")
    assert "python -m ambo.validate.report" in text
    recover_block = text.split("recover:")[1].split("sensitivity:")[0]
    assert "STUB" not in recover_block


def test_missing_parquet_error_names_fit_synthetic() -> None:
    source = (repo_root() / "src/ambo/validate/report.py").read_text(encoding="utf-8")
    assert "make fit-synthetic" in source


def test_generate_report_section_order(tmp_path: Path) -> None:
    dest = generate_recovery_report(output_dir=tmp_path)
    markdown = dest.read_text(encoding="utf-8")
    assert section_headings_in(markdown) == list(SECTION_HEADINGS)
    closing = markdown.split("## What this does and does not prove", 1)[1]
    assert len(closing.strip()) >= _CLOSING_MIN_CHARS
    assert "MD-020" in closing
    assert "lift test" in closing.lower()
    assert "PASS" in markdown or "FAIL" in markdown
    assert (tmp_path / "roas_P-SA.png").is_file()
    assert (tmp_path / "curves_P-SC.png").is_file()
    assert (tmp_path / "metrics_P-SA.json").is_file()
    assert (tmp_path / "gates_P-SB.json").is_file()
