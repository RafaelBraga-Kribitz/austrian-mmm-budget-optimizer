"""Model-report integrity of the Power BI project under dashboards/.

The report (PBIR JSON) and the semantic model (TMDL) are text, so they can be checked
without Power BI Desktop: every field a visual uses must exist in the model, every
relationship must join existing columns, every table must load a file the export
writes, and the pages must be the ones docs/dashboard_handoff.md specifies, each with
its German subtitle. Schema validation of the JSON is scripts/validate_pbip.py; it needs
a local copy of the Microsoft schemas and is not run here.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DASH = ROOT / "dashboards"
MODEL = DASH / "MMM.SemanticModel" / "definition"
REPORT = DASH / "MMM.Report"
PAGES = REPORT / "definition" / "pages"
HANDOFF = ROOT / "docs" / "dashboard_handoff.md"
EXPORTS = ROOT / "reports" / "exports"

# Measures that return text; a numeric format string does not apply to them.
TEXT_MEASURES = {
    "Verdict", "Channels held by the rule", "Held by rule", "Platform over true",
    "Parameters covered label", "Fits passing label",
}

NAME = r"(?:'(?:[^']|'')+'|[A-Za-z_][\w]*)"


def unquote(name: str) -> str:
    name = name.strip()
    if name.startswith("'") and name.endswith("'"):
        return name[1:-1].replace("''", "'")
    return name


def parse_tmdl() -> dict:
    """Tables with their columns and measures (and per-measure properties) from TMDL."""
    tables: dict[str, dict] = {}
    for path in sorted((MODEL / "tables").glob("*.tmdl")):
        lines = path.read_text(encoding="utf-8").split("\n")
        current = None
        table = None
        pending_doc = False
        for line in lines:
            m = re.match(rf"^table ({NAME})\s*$", line)
            if m:
                table = unquote(m.group(1))
                tables[table] = {"columns": {}, "measures": {}, "partitions": [], "file": path}
                continue
            if line.startswith("\t///"):
                pending_doc = True
                continue
            m = re.match(rf"^\t(column|measure) ({NAME})", line)
            if m:
                kind = m.group(1) + "s"
                current = {"description": pending_doc, "props": {}}
                tables[table][kind][unquote(m.group(2))] = current
                pending_doc = False
                continue
            m = re.match(rf"^\tpartition ({NAME}) = (\w+)", line)
            if m:
                current = {"kind": m.group(2), "source": []}
                tables[table]["partitions"].append(current)
                continue
            if current is not None and line.startswith("\t\t"):
                prop = re.match(r"^\t\t(\w+)(?::\s*(.*))?$", line)
                if prop and "props" in current:
                    current["props"][prop.group(1)] = (prop.group(2) or "").strip()
                if "source" in current:
                    current["source"].append(line.strip())
            if line and not line.startswith("\t"):
                pending_doc = False
    return tables


@pytest.fixture(scope="module")
def model() -> dict:
    return parse_tmdl()


def visuals() -> list[tuple[Path, dict]]:
    return [(p, json.loads(p.read_text(encoding="utf-8")))
            for p in sorted(PAGES.glob("*/visuals/*/visual.json"))]


def field_refs(obj, aliases=None):
    """Yield (kind, table, property) for every Column/Measure reference in a PBIR object."""
    aliases = dict(aliases or {})
    if isinstance(obj, dict):
        if isinstance(obj.get("From"), list):
            aliases.update({f["Name"]: f["Entity"] for f in obj["From"] if "Entity" in f})
        for kind in ("Column", "Measure"):
            ref = obj.get(kind)
            if isinstance(ref, dict) and "Property" in ref:
                src = ref["Expression"]["SourceRef"]
                table = src.get("Entity") or aliases.get(src.get("Source"))
                yield kind, table, ref["Property"]
        for value in obj.values():
            yield from field_refs(value, aliases)
    elif isinstance(obj, list):
        for value in obj:
            yield from field_refs(value, aliases)


def literal(container: dict, *path: str):
    node = container
    for key in path:
        node = node[key] if not isinstance(node, list) else node[0][key]
    return node["expr"]["Literal"]["Value"]


def spec_pages() -> list[tuple[str, str]]:
    """(display name, German subtitle) per page, from the Pages table of the handoff."""
    rows = re.findall(r"^\| (\d) ([^|]+?) \| ([^|]+?) \|", HANDOFF.read_text(encoding="utf-8"),
                      re.M)
    return [(name.strip(), subtitle.strip()) for _, name, subtitle in sorted(rows)]


def test_every_project_file_is_valid_json_without_bom():
    files = [p for p in DASH.rglob("*") if p.suffix in {".json", ".pbir", ".pbism", ".pbip"}
             and "html" not in p.relative_to(DASH).parts]
    assert len(files) > 20
    for path in files:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), path
        json.loads(raw.decode("utf-8"))


def test_project_links_resolve():
    pbip = json.loads((DASH / "MMM.pbip").read_text(encoding="utf-8"))
    assert (DASH / pbip["artifacts"][0]["report"]["path"]).is_dir()
    pbir = json.loads((REPORT / "definition.pbir").read_text(encoding="utf-8"))
    assert (REPORT / pbir["datasetReference"]["byPath"]["path"]).resolve() == (
        DASH / "MMM.SemanticModel").resolve()
    assert (DASH / "MMM.SemanticModel" / "definition.pbism").exists()


def test_every_visual_field_exists_in_the_model(model):
    missing = []
    count = 0
    for path, vis in visuals():
        for kind, table, prop in field_refs(vis):
            count += 1
            bucket = "measures" if kind == "Measure" else "columns"
            if table not in model or prop not in model[table][bucket]:
                missing.append(f"{path.parent.name}: {kind} {table}[{prop}]")
    assert count > 50
    assert not missing, missing


def test_projection_query_refs_match_their_field():
    for path, vis in visuals():
        for role in vis["visual"].get("query", {}).get("queryState", {}).values():
            for proj in role["projections"]:
                kind, ref = next(iter(proj["field"].items()))
                expected = f"{ref['Expression']['SourceRef']['Entity']}.{ref['Property']}"
                assert proj["queryRef"] == expected, (path.parent.name, proj["queryRef"])


def test_relationships_join_existing_columns(model):
    text = (MODEL / "relationships.tmdl").read_text(encoding="utf-8")
    ends = re.findall(rf"(fromColumn|toColumn): ({NAME})\.({NAME})", text)
    assert len(ends) >= 2 and len(ends) % 2 == 0
    for _, table, column in ends:
        t, c = unquote(table), unquote(column)
        assert t in model and c in model[t]["columns"], f"{t}[{c}]"
    pairs = list(zip(ends[0::2], ends[1::2], strict=True))
    for (_, ft, _), (_, tt, _) in pairs:
        assert unquote(ft) != unquote(tt)
    assert "crossFilteringBehavior: bothDirections" not in text


def test_every_measure_is_described_and_formatted(model):
    problems = []
    for table, t in model.items():
        for name, m in t["measures"].items():
            if not m["description"]:
                problems.append(f"{table}[{name}] has no /// description")
            if "displayFolder" not in m["props"]:
                problems.append(f"{table}[{name}] has no displayFolder")
            if "formatString" not in m["props"] and name not in TEXT_MEASURES:
                problems.append(f"{table}[{name}] has no formatString")
    assert not problems, problems


def test_every_export_is_loaded_through_the_path_parameter(model):
    assert re.search(r"expression ExportsPath = .*IsParameterQuery = true",
                     (MODEL / "expressions.tmdl").read_text(encoding="utf-8"))
    loaded = set()
    for t in model.values():
        for part in t["partitions"]:
            source = " ".join(part["source"])
            if part["kind"] == "m":
                assert "ExportsPath" in source
                assert "File.Contents(Folder & " in source
                loaded.update(re.findall(r'"([\w]+\.csv)"', source))
    exports = {p.name for p in EXPORTS.glob("*.csv")}
    assert loaded == exports, (sorted(exports - loaded), sorted(loaded - exports))


def test_date_table_is_marked(model):
    cal = model["Calendar"]
    text = cal["file"].read_text(encoding="utf-8")
    assert "\tdataCategory: Time" in text
    assert "isKey" in cal["columns"]["Date"]["props"]


def test_pages_match_the_handoff_spec():
    expected = spec_pages()
    assert len(expected) == 4
    meta = json.loads((PAGES / "pages.json").read_text(encoding="utf-8"))
    names = []
    for pid in meta["pageOrder"]:
        page = json.loads((PAGES / pid / "page.json").read_text(encoding="utf-8"))
        assert (page["width"], page["height"]) == (1280, 720)
        names.append(page["displayName"])
    assert names == [name for name, _ in expected]
    for pid, (_, subtitle) in zip(meta["pageOrder"], expected, strict=True):
        texts = []
        for path in (PAGES / pid / "visuals").glob("*/visual.json"):
            vis = json.loads(path.read_text(encoding="utf-8"))
            if vis["visual"]["visualType"] == "textbox":
                for para in vis["visual"]["objects"]["general"][0]["properties"]["paragraphs"]:
                    texts.append("".join(run["value"] for run in para["textRuns"]))
        assert subtitle in texts, (pid, subtitle)
        assert any(t.startswith("Source: ") for t in texts), pid


def test_accessibility_alt_text_and_tab_order():
    for page in PAGES.iterdir():
        if not page.is_dir():
            continue
        orders = []
        for path in (page / "visuals").glob("*/visual.json"):
            vis = json.loads(path.read_text(encoding="utf-8"))
            vtype = vis["visual"]["visualType"]
            alt = literal(vis["visual"]["visualContainerObjects"], "general", "properties",
                          "altText")
            tab = vis["position"]["tabOrder"]
            if vtype == "shape":
                assert alt == "''" and tab == -9999000, path
                continue
            text = alt[1:-1].replace("''", "'")
            assert 12 < len(text) <= 150, (path, text)
            orders.append(tab)
        assert len(orders) == len(set(orders)), page.name
        assert all(t > 0 for t in orders), page.name


def test_theme_is_registered_and_present():
    report = json.loads((REPORT / "definition" / "report.json").read_text(encoding="utf-8"))
    custom = report["themeCollection"]["customTheme"]
    items = [i for pkg in report["resourcePackages"] for i in pkg["items"]
             if pkg["type"] == "RegisteredResources"]
    assert any(i["name"] == custom["name"] and i["type"] == "CustomTheme" for i in items)
    theme = REPORT / "StaticResources" / "RegisteredResources" / custom["name"]
    data = json.loads(theme.read_text(encoding="utf-8"))
    assert data["background"] and len(data["dataColors"]) >= 5


def test_money_is_never_formatted_as_euro():
    for path in list(MODEL.rglob("*.tmdl")) + list(PAGES.rglob("*.json")):
        text = path.read_text(encoding="utf-8")
        assert "€" not in text and "EUR" not in text, path


def test_schema_check_skips_cleanly_without_a_schema_folder(monkeypatch, capsys):
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("validate_pbip",
                                                  ROOT / "scripts" / "validate_pbip.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.delenv("PBIP_SCHEMAS", raising=False)
    monkeypatch.setattr(sys, "argv", ["validate_pbip.py"])
    assert module.main() == 0
    assert "skipped" in capsys.readouterr().out
