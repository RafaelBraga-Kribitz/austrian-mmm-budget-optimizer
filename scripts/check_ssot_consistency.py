"""Numeric-SSOT reconciliation check (GB-301/GB-302/GB-303, SPEC-09 sections 3-4).

Implements: REQ-dl8-quality

Owning spec: `docs/SPEC-09_governance_quality.md` sections 3-4;
`docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md` section 6. The M0 scope
decision is D-17 (`.planning/phases/01-repository-foundation/01-CONTEXT.md`): this is
a real, vacuously-correct-today predicate, not a stub. Phase 5 EXTENDS this script in
place -- it does not replace it. `reports/NUMERIC_SSOT.md` does not exist yet at M0,
so the reconciliation below currently has nothing to reconcile from; the moment the
SSOT file and the documents it reconciles against exist, this check has real work.

GB-301/GB-302: `reports/NUMERIC_SSOT.md` is a single markdown table, generated only
by `scripts/generate_ssot.py` (Phase 5+), with exactly six columns: `key`, `value`,
`unit`, `tag`, `produced_by`, `updated_at`. `parse_ssot()` is the one place that reads
this table; a malformed table -- the wrong header, a row with the wrong cell count,
an empty key -- is a real error, not a row silently skipped.

GB-303: every numeric literal carrying an SSOT-adjacent unit (`a€`, `%`, `×`/`x`,
`weeks`) in `README.md`, `docs/EXEC_SUMMARY.md` or `reports/recovery/RECOVERY_REPORT.md`
must match some SSOT row's value, within that row's own printed rounding precision,
or be named (with a justification) in `config/ssot_whitelist.yaml`. None of the three
reconciled documents carries a tagged number yet at M0 -- README.md is a Phase 1
scaffold with no numeric claims (D-28) -- so this reconciliation currently runs over
an empty candidate set; absence of any one of the three documents is not itself an
error, it is simply nothing to reconcile from that source.

Pre-condition absent -- `reports/NUMERIC_SSOT.md` does not exist -- is a real outcome
this predicate reports explicitly, not a skip: exit 0 with a notice naming the
expected path, so a reader can tell the check ran and found nothing to reconcile, not
that it was bypassed.

Conventions matched to `scripts/leak_scan.py`: exit 0 clean, 1 violations found, 2
usage error; notices on stdout, errors and violations on stderr.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

import yaml

from ambo.common.config import repo_root
from ambo.common.errors import AmboError

SSOT_PATH = "reports/NUMERIC_SSOT.md"

SSOT_REQUIRED_COLUMNS: tuple[str, ...] = (
    "key",
    "value",
    "unit",
    "tag",
    "produced_by",
    "updated_at",
)

# GB-303: the documents whose numeric literals are reconciled against the SSOT, when
# they exist. Absence of any one is not an error -- see module docstring.
RECONCILED_DOCS: tuple[str, ...] = (
    "README.md",
    "docs/EXEC_SUMMARY.md",
    "reports/recovery/RECOVERY_REPORT.md",
)

WHITELIST_PATH = "config/ssot_whitelist.yaml"

# A number immediately preceded by `a€`, or immediately followed by one of the other
# SSOT-adjacent units GB-303 names: `%`, `×`/`x` (multiplier), `weeks`/`week`.
_LITERAL_RE = re.compile(
    r"(?:a€\s?(?P<val_prefixed>-?\d[\d.,]*)"
    r"|(?P<val_suffixed>-?\d[\d.,]*)\s?(?P<unit_suffixed>%|×|x\b|weeks?\b))"
)


class SsotError(AmboError):
    """Raised on a malformed `reports/NUMERIC_SSOT.md` table, or a malformed
    `config/ssot_whitelist.yaml` -- an error, not a notice, because the file exists
    but cannot be trusted as written."""


def parse_ssot(path: Path) -> dict[str, dict[str, str]]:
    """Parse the GB-301 markdown table at `path` into rows keyed by `key`.

    Raises `SsotError` on any malformed table -- a header that is not exactly
    `SSOT_REQUIRED_COLUMNS`, a row with the wrong cell count, an empty key -- rather
    than silently skipping the offending row.
    """
    text = path.read_text(encoding="utf-8")
    table_lines = [line for line in text.splitlines() if line.strip().startswith("|")]
    if len(table_lines) < 2:
        raise SsotError(f"{path}: no markdown table found (need a header row and a separator row)")

    header = tuple(cell.strip() for cell in table_lines[0].strip().strip("|").split("|"))
    if header != SSOT_REQUIRED_COLUMNS:
        raise SsotError(
            f"{path}: header must be exactly {' | '.join(SSOT_REQUIRED_COLUMNS)}, "
            f"got {' | '.join(header)}"
        )

    rows: dict[str, dict[str, str]] = {}
    for line in table_lines[2:]:  # skip the header row and its '---' separator
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(SSOT_REQUIRED_COLUMNS):
            raise SsotError(
                f"{path}: row does not have exactly {len(SSOT_REQUIRED_COLUMNS)} columns: {line!r}"
            )
        row = dict(zip(SSOT_REQUIRED_COLUMNS, cells, strict=True))
        if not row["key"]:
            raise SsotError(f"{path}: row has an empty key: {line!r}")
        rows[row["key"]] = row
    return rows


def _decimals(value: str) -> int:
    return len(value.split(".", 1)[1]) if "." in value else 0


def _normalize_unit(unit: str) -> str:
    """Normalize a unit spelling to one canonical form: `x`/`×` both become `×`,
    everything else is lowercased. Applied identically to the literal's unit and
    the SSOT row's own unit (WR-01) -- normalizing only one side let a document
    spelling a multiplier `×` and an SSOT table spelling it `x` (or vice versa)
    fail to reconcile even though they agree."""
    return "×" if unit in ("x", "×") else unit.lower()


# A trailing comma followed by exactly one or two digits is never a valid
# thousands-grouping comma under this parser's period-decimal, comma-thousands
# convention -- a genuine thousands group always ends in exactly three digits
# (`1,234`). That shape is always a decimal comma instead: either a bare one
# (`234,56`) or the trailing decimal half of an Austrian period-thousands/
# comma-decimal literal (`1.234,56`). WR-02: reject it explicitly rather than
# let `float(value.replace(",", ""))` either raise `ValueError` (silently
# treated as "no match", the `1.234,56` case -- multiple `.` after stripping the
# comma) or -- worse -- silently succeed at the wrong magnitude (the `234,56`
# case -- comma-stripping alone yields `23456`).
_AMBIGUOUS_DECIMAL_COMMA_RE = re.compile(r",\d{1,2}$")


def _reject_if_ambiguous_decimal_comma(value: str) -> None:
    """Raise `SsotError` if `value` has the shape of a decimal comma (see module-
    level regex comment) -- this parser's canonical numeric-literal format is
    period-decimal, and an ambiguous literal is a real error, not a silent
    non-match."""
    if _AMBIGUOUS_DECIMAL_COMMA_RE.search(value):
        raise SsotError(
            f"{value!r}: ends in a comma followed by one or two digits, which is "
            "never a valid thousands-grouping comma (a thousands group is always "
            "exactly three digits) and is always the shape of a decimal comma -- "
            "this parser's canonical numeric-literal format is period-decimal "
            "(e.g. '1234.56' or '1,234.56'), not comma-decimal; rewrite the "
            "literal (or the SSOT row) to match, or document it in "
            "config/ssot_whitelist.yaml"
        )


def _matches_any_row(value: str, unit: str, rows: dict[str, dict[str, str]]) -> bool:
    """True if `value` (with adjacent `unit`) equals some SSOT row's own value,
    rounded to that row's own printed decimal precision (round-half-even, GB-303),
    and the row's unit is compatible with the literal's unit."""
    _reject_if_ambiguous_decimal_comma(value)
    try:
        parsed = float(value.replace(",", ""))
    except ValueError:
        return False
    unit_norm = _normalize_unit(unit)
    for row in rows.values():
        row_unit = _normalize_unit(row["unit"])
        if unit_norm not in row_unit and row_unit not in unit_norm:
            continue
        _reject_if_ambiguous_decimal_comma(row["value"])
        try:
            row_value = float(row["value"].replace(",", ""))
        except ValueError:
            continue
        precision = _decimals(row["value"])
        if round(parsed, precision) == round(row_value, precision):
            return True
    return False


def _load_whitelist(root: Path) -> set[str]:
    """Return the whitelisted literal strings from `config/ssot_whitelist.yaml`, or
    an empty set when the file does not exist. Parsing itself enforces that every
    entry names both `literal` and a non-empty `justification` -- an entry without a
    justification is a malformed whitelist, not a silently-accepted one."""
    path = root / WHITELIST_PATH
    if not path.is_file():
        return set()
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(raw, list):
        raise SsotError(f"{path}: expected a YAML list of whitelist entries")
    literals: set[str] = set()
    for entry in raw:
        is_valid = isinstance(entry, dict) and entry.get("literal") and entry.get("justification")
        if not is_valid:
            raise SsotError(
                f"{path}: every whitelist entry needs a non-empty 'literal' and "
                f"'justification', got {entry!r}"
            )
        literals.add(str(entry["literal"]))
    return literals


def _reconcile(root: Path, rows: dict[str, dict[str, str]]) -> list[str]:
    """Extract SSOT-adjacent numeric literals from whichever `RECONCILED_DOCS`
    exist, and return the ones that neither match an SSOT row (within rounding) nor
    appear in the whitelist. An empty return means everything reconciled."""
    whitelist = _load_whitelist(root)
    unmatched: list[str] = []
    for rel in RECONCILED_DOCS:
        doc_path = root / rel
        if not doc_path.is_file():
            continue
        text = doc_path.read_text(encoding="utf-8")
        for match in _LITERAL_RE.finditer(text):
            literal_text = match.group(0)
            if literal_text in whitelist:
                continue
            if match.group("val_prefixed") is not None:
                value, unit = match.group("val_prefixed"), "a€"
            else:
                value, unit = match.group("val_suffixed"), match.group("unit_suffixed")
            if _matches_any_row(value, unit, rows):
                continue
            unmatched.append(f"{rel}: {literal_text!r}")
    return unmatched


class _UsageError(Exception):
    """Raised by `_ArgParser.error` instead of calling `sys.exit` directly, so
    `main()` stays a plain argv -> exit-code function with a single process-exit
    call site (the module's own `__main__` guard)."""


class _ArgParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # type: ignore[override]
        raise _UsageError(message)


def _build_arg_parser() -> _ArgParser:
    parser = _ArgParser(
        prog="check_ssot_consistency.py",
        description="GB-301/GB-302/GB-303 numeric-SSOT reconciliation check.",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Override the scanned repository root (default: the repository root).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse `argv`, run the GB-301..303 predicate, print its result, and return the
    process exit code: 0 clean (including the nothing-to-reconcile notice), 1
    violation(s) found, 2 usage error. Never calls `sys.exit` itself.
    """
    parser = _build_arg_parser()
    try:
        args = parser.parse_args(argv)
    except _UsageError as exc:
        print(parser.format_usage(), end="", file=sys.stderr)
        print(f"check_ssot_consistency.py: error: {exc}", file=sys.stderr)
        return 2

    root = Path(args.root).resolve() if args.root else repo_root()
    ssot_path = root / SSOT_PATH

    if not ssot_path.is_file():
        print(
            f"check_ssot_consistency: no {SSOT_PATH} found at {ssot_path} -- nothing "
            "to reconcile. Check ran, found nothing to do."
        )
        return 0

    try:
        rows = parse_ssot(ssot_path)
        unmatched = _reconcile(root, rows)
    except SsotError as exc:
        print(f"check_ssot_consistency: {exc}", file=sys.stderr)
        return 1

    if unmatched:
        print("check_ssot_consistency: unreconciled numeric literal(s):", file=sys.stderr)
        for item in unmatched:
            print(f"  {item}", file=sys.stderr)
        return 1

    print(f"check_ssot_consistency: {SSOT_PATH} parsed ({len(rows)} row(s)); all reconciled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
