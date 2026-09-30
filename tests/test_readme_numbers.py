"""Every number in the rendered documents must exist somewhere under reports/.

README.md, reports/memo_EN.md and docs/summary_de.md are written by renderers under
scripts/ that record the values they inserted in reports/*_values.json; the raw
artifacts (CSV, JSON, Markdown) are searched as well. A number that appears in a
document but in no file under reports/ means someone typed a metric by hand.

The committed documents must also equal a fresh render from the committed reports,
so a pipeline rerun that is not followed by a rerender fails here, and the memo PDF
must have been built from the committed memo.
"""

import hashlib
import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
MEMO = ROOT / "reports" / "memo_EN.md"
SUMMARY_DE = ROOT / "docs" / "summary_de.md"
REPORTS = ROOT / "reports"
SCRIPTS = ROOT / "scripts"

NUMBER = re.compile(r"(?<![\w./-])\d+(?:\.\d+)?(?![\w/])")
NUMBER_DE = re.compile(r"(?<![\w./-])\d+(?:,\d+)?(?![\w/])")
FORBIDDEN_WORDS = ("governance", "workflow", "agent")  # tool names are checked repo-wide


def _report_text(exclude: tuple[str, ...] = ()) -> str:
    chunks = []
    for path in REPORTS.rglob("*"):
        if path.name in exclude:
            continue
        if path.suffix.lower() in {".csv", ".json", ".md", ".txt"}:
            chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
            chunks.append(path.name)
    return "\n".join(chunks)


def _strip_paths(text: str) -> str:
    text = re.sub(r"\(reports/[^)]*\)", "", text)  # image and file links carry paths
    text = re.sub(r"`?reports/\S+", "", text)
    text = re.sub(r"`?data/\S+", "", text)
    text = re.sub(r"`?scripts/\S+", "", text)
    return text


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def readme() -> str:
    if not README.exists() or not (REPORTS / "readme_values.json").exists():
        pytest.skip("README not rendered yet")
    return README.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def memo() -> str:
    if not MEMO.exists() or not (REPORTS / "memo_values.json").exists():
        pytest.skip("memo not rendered yet")
    return MEMO.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def summary_de() -> str:
    if not SUMMARY_DE.exists() or not (REPORTS / "summary_de_values.json").exists():
        pytest.skip("German summary not rendered yet")
    return SUMMARY_DE.read_text(encoding="utf-8")


def test_every_number_in_readme_comes_from_reports(readme):
    text = _report_text()
    numbers = set(NUMBER.findall(_strip_paths(readme)))
    missing = sorted(n for n in numbers if n not in text)
    assert not missing, f"numbers in README.md not found under reports/: {missing}"


def test_every_number_in_memo_comes_from_reports(memo):
    # the memo itself lives under reports/, so it may not vouch for its own numbers
    text = _report_text(exclude=(MEMO.name,))
    body = memo.split("## Numbers in this memo")[0]
    body = body.replace("{width=5.4in}", "")
    numbers = set(NUMBER.findall(_strip_paths(body))) - {"1", "2", "3", "4", "5", "6"}
    missing = sorted(n for n in numbers if n not in text)
    assert not missing, f"numbers in memo_EN.md not found under reports/: {missing}"


def test_every_number_in_summary_de_comes_from_reports(summary_de):
    text = _report_text()
    numbers = {n.replace(",", ".") for n in NUMBER_DE.findall(_strip_paths(summary_de))}
    text_de = text + "\n" + (REPORTS / "summary_de_values.json").read_text(encoding="utf-8")
    missing = sorted(
        n for n in numbers if n not in text and n.replace(".", ",") not in text_de
    )
    assert not missing, f"numbers in docs/summary_de.md not found under reports/: {missing}"


def test_readme_matches_a_fresh_render(readme):
    render_readme = _load("render_readme")
    fresh = render_readme.render(render_readme.last_date())
    assert fresh == readme, (
        "README.md differs from scripts/render_readme.py output; edit "
        "scripts/readme_template.md and rerun the renderer instead of editing README.md"
    )


def test_memo_matches_a_fresh_render(memo):
    render_memo = _load("render_memo")
    assert render_memo.render() == memo, "rerun scripts/render_memo.py --pdf"


def test_memo_pdf_was_built_from_the_committed_memo(memo):
    stamp = REPORTS / "memo_EN.pdf.sha256"
    assert stamp.exists(), "build the PDF with scripts/render_memo.py --pdf"
    recorded = stamp.read_text(encoding="utf-8").split()[0]
    assert recorded == hashlib.sha256(MEMO.read_bytes()).hexdigest(), (
        "reports/memo_EN.pdf is older than reports/memo_EN.md; rerun "
        "scripts/render_memo.py --pdf"
    )


def test_summary_de_matches_a_fresh_render(summary_de):
    render_summary_de = _load("render_summary_de")
    assert render_summary_de.render(render_summary_de.readme_date()) == summary_de, (
        "rerun scripts/render_summary_de.py"
    )


def test_documents_share_one_date(readme, summary_de):
    date_readme = re.search(r"Last validated: (\d{4}-\d{2}-\d{2})", readme).group(1)
    date_de = re.search(r"Stand: (\d{4}-\d{2}-\d{2})", summary_de).group(1)
    assert date_readme == date_de


def test_readme_has_no_forbidden_words_or_dashes(readme):
    lower = readme.lower()
    hits = [w for w in FORBIDDEN_WORDS if w in lower]
    assert not hits, hits
    assert "—" not in readme, "em dash in README"
    assert not re.search(r"[\U0001F300-\U0001FAFF☀-➿]", readme), "emoji in README"
