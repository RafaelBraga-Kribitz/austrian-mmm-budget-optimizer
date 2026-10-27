# ADR-010: Power BI as a PBIP text project, plus a static HTML twin

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** Rafael Braga-Kribitz
- **Supersedes:** the SPEC-07 sections 2 and 4 row of ADR-009 section 1, for the dashboard only (`dashboards/ambo.pbix`, `docs/assets/dashboard_p1..p4.png`). The five executive charts and `reports/EXEC_SUMMARY.md` stay as ADR-009 records them.
- **Related:** STATUS.md D-29; ADR-009; `docs/dashboard_handoff.md`; `dashboards/README.md`; SPEC-07 RB-401 to RB-406

---

## Context

`docs/dashboard_handoff.md` specifies a four-page Power BI dashboard on the CSV feed in
`reports/exports/`, and STATUS listed the build as human work: SPEC-07 RB-406 asked for
a committed `.pbix`. A `.pbix` is a binary that only Power BI Desktop writes. It cannot
be authored, reviewed in a diff or tested in CI, and nothing checks that its visuals
still point at fields the model has after the export changes.

Power BI Desktop also saves a report as a Power BI Project (PBIP): the semantic model
as TMDL text and the report as PBIR JSON, one file per page and per visual, each JSON
file naming its published schema. PBIR is the default report format in current Desktop
releases; older releases open it only with the preview features for PBIP, TMDL and the
enhanced report format switched on.

A reader without Power BI Desktop (most reviewers of a public repository) still sees no
dashboard at all.

## Decision

1. The dashboard is a PBIP project in `dashboards/` (`MMM.pbip`, `MMM.SemanticModel/`,
   `MMM.Report/`), not a `.pbix`. The model loads the ten export CSV files through Power
   Query with one text parameter, `ExportsPath`; no table reads the model or the
   posterior. Pages, German subtitles and captions follow `docs/dashboard_handoff.md`.
2. `tests/test_dashboard_pbip.py` checks model against report without Desktop: every
   field a visual uses exists in the TMDL, every relationship joins existing columns,
   every export file is loaded through the parameter, every measure carries a
   description and a format string, the pages and subtitles match the handoff, every
   data visual has alt text and a tab order, the theme is registered.
   `scripts/validate_pbip.py` validates every JSON file against its declared Microsoft
   schema from a local schema copy and skips with exit 0 when none is given, so CI needs
   no network.
3. A static HTML twin, `dashboards/html/index.html`, shows the same four pages from the
   same CSV files. `scripts/build_dashboard_html.py` writes it: one self-contained file,
   data inline as JSON, charts as inline SVG drawn by embedded vanilla JavaScript, no
   network request, no backend. The build is deterministic and
   `tests/test_dashboard_html.py` fails when the committed page differs from a fresh
   build or when its headline figures differ from the CSV files.
4. Screenshots of the HTML twin are committed as `docs/assets/dashboard_html_p1..p4.png`
   and labelled as the HTML twin wherever they appear. Power BI screenshots follow the
   Desktop step under their own names.

## Alternatives rejected

- A `.pbix` built by hand in Desktop: binary, untestable, and the dashboard stays
  missing until someone with Desktop has a free afternoon.
- The HTML twin only: drops the Power BI deliverable the handoff and the target roles ask
  for.
- A JavaScript charting library from a CDN: the page would stop rendering offline and
  its numbers would depend on code outside the repository.
- Resurrecting the warehouse and `exports/` marts of SPEC-03 as the model's source:
  STATUS D-29 forbids it; the CSV feed is the contract.

## Consequences

- The Desktop step stays human: open `dashboards/MMM.pbip`, set `ExportsPath`, refresh,
  compare the cards with the README, save, take the Power BI screenshots. Until then
  nobody has seen the report render in Desktop, and visual formatting (colours per
  series, axis titles, slicer defaults) is as written in the JSON, not as Desktop shows
  it. The checklist is in `dashboards/README.md`.
- After the first Desktop save, Desktop owns the PBIR and TMDL files; edits there show
  up as text diffs, and the integrity test keeps guarding the field references.
- The HTML twin must be rebuilt after every export: `uv run python
  scripts/build_dashboard_html.py`. The test makes a stale page fail CI.
- Two renderings of one page set can drift in what they emphasise. The handoff document
  stays the single specification for both; a page change starts there.
- Interval and money conventions are unchanged: 90 percent intervals, amounts in the
  demo dataset's money units with the verbatim caption, never a euro sign.
