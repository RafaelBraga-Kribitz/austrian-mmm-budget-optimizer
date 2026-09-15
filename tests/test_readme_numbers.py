"""Every number in README.md must exist somewhere under reports/.

The renderer records the values it inserted in reports/readme_values.json; the raw
artifacts (CSV, JSON, Markdown) are searched as well. A number that appears in the
README but in no file under reports/ means someone typed a metric by hand.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
REPORTS = ROOT / "reports"

NUMBER = re.compile(r"(?<![\w./-])\d+(?:\.\d+)?(?![\w/])")
FORBIDDEN_WORDS = ("governance", "workflow", "agent")  # tool names are checked repo-wide


def _report_text() -> str:
    chunks = []
    for path in REPORTS.rglob("*"):
        if path.suffix.lower() in {".csv", ".json", ".md", ".txt"}:
            chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
            chunks.append(path.name)
    return "\n".join(chunks)


@pytest.fixture(scope="module")
def readme() -> str:
    if not README.exists() or not (REPORTS / "readme_values.json").exists():
        pytest.skip("README not rendered yet")
    return README.read_text(encoding="utf-8")


def test_every_number_in_readme_comes_from_reports(readme):
    text = _report_text()
    prose = re.sub(r"\(reports/[^)]*\)", "", readme)  # image and file links carry paths
    prose = re.sub(r"reports/\S+", "", prose)
    prose = re.sub(r"data/\S+", "", prose)
    numbers = set(NUMBER.findall(prose))
    missing = sorted(n for n in numbers if n not in text)
    assert not missing, f"numbers in README.md not found under reports/: {missing}"


def test_readme_has_no_forbidden_words_or_dashes(readme):
    lower = readme.lower()
    hits = [w for w in FORBIDDEN_WORDS if w in lower]
    assert not hits, hits
    assert "—" not in readme, "em dash in README"
    assert not re.search(r"[\U0001F300-\U0001FAFF☀-➿]", readme), "emoji in README"
