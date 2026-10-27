"""The static HTML twin of the dashboard: deterministic, self-contained, true to the CSVs."""

import csv
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXPORTS = ROOT / "reports" / "exports"
PAGE = ROOT / "dashboards" / "html" / "index.html"


def _load():
    spec = importlib.util.spec_from_file_location(
        "build_dashboard_html", ROOT / "scripts" / "build_dashboard_html.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_dashboard_html"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def build():
    return _load()


@pytest.fixture(scope="module")
def html(build) -> str:
    return build.render()


def rows(name: str) -> list[dict]:
    with open(EXPORTS / name, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def kpi(html: str, key: str) -> str:
    m = re.search(rf'data-kpi="{re.escape(key)}"><p class="kpi-label">[^<]*</p>'
                  rf'<p class="kpi-value">([^<]*)</p>', html)
    assert m, key
    return m.group(1)


def test_build_is_deterministic_and_committed(build, html):
    assert build.render() == html
    assert PAGE.read_text(encoding="utf-8") == html, (
        "dashboards/html/index.html is stale; run scripts/build_dashboard_html.py")


def test_headline_numbers_equal_the_export_files(html):
    gain = {r["scenario"]: r for r in rows("recommendation_gain.csv")}
    for scenario, g in gain.items():
        assert kpi(html, f"{scenario}-gain-median") == (
            f"{float(g['gain_pct_of_contribution_median']):.1f}%")
        assert kpi(html, f"{scenario}-gain-p10") == (
            f"{float(g['gain_pct_of_contribution_p10']):.1f}%")
        loss = 100 * float(g["probability_gain_negative"])
        assert kpi(html, f"{scenario}-loss") == f"{loss:.1f}%"
        assert kpi(html, f"{scenario}-budget") == f"{float(g['total_weekly_budget']):,.0f}"
    params = rows("proof_parameter_recovery.csv")
    covered = sum(r["covered"] == "True" for r in params)
    assert kpi(html, "params") == f"{covered} of {len(params)}"
    gates = rows("proof_sampler_gates.csv")
    assert kpi(html, "gates") == f"{sum(r['pass_all'] == 'True' for r in gates)} of {len(gates)}"
    roas = rows("roas_summary.csv")
    top = max(roas, key=lambda r: float(r["share_median"]))
    assert kpi(html, "top-share") == f"{top['channel']} {100 * float(top['share_median']):.1f}%"


def test_embedded_data_is_the_export_files(build, html):
    m = re.search(r'<script type="application/json" id="dashboard-data">(.*?)</script>', html,
                  re.S)
    data = json.loads(m.group(1).replace("<\\/", "</"))
    for name in build.FILES:
        source = rows(name)
        embedded = data[name.removesuffix(".csv")]
        assert len(embedded) == len(source), name
        for a, b in zip(embedded, source, strict=True):
            assert a == {k: build.parse(v) for k, v in b.items()}, name


def test_no_network_resources(html):
    assert not re.search(r'<(script|link|img|iframe)[^>]+(src|href)="(https?:)?//', html, re.I)
    assert "@import" not in html and "url(http" not in html
    assert "€" not in html


def test_pages_tabs_and_german_subtitles(build, html):
    assert html.count('role="tab" ') == 4 and 'role="tablist"' in html
    for slug, _name, subtitle in build.PAGES:
        assert f'id="panel-{slug}" role="tabpanel"' in html
        assert f'<p class="subtitle" lang="de">{subtitle}</p>' in html


def test_captions_copied_verbatim(build, html):
    handoff = (ROOT / "docs" / "dashboard_handoff.md").read_text(encoding="utf-8")
    flat = " ".join(handoff.split())
    assert build.MONEY_CAPTION in flat and build.GAIN_CAPTION in flat
    assert build.MONEY_CAPTION in html and build.GAIN_CAPTION in html


def test_offline_channels_show_no_platform_report(html):
    gap = rows("proof_attribution_gap.csv")
    offline = [r["channel"] for r in gap if r["platform_over_true_pct"] == ""]
    assert offline
    for channel in offline:
        assert re.search(rf"<th scope=row>{re.escape(channel)}</th>(?:<td[^>]*>[^<]*</td>)*"
                         r"<td class=\"num\">no platform report</td>", html), channel
