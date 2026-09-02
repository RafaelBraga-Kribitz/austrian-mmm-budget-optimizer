"""Registry-driven, byte-stable mart-to-CSV export writer (T-205, D-01..D-05).

Implements: REQ-dl1-reproducible-pipeline, REQ-grain-and-windows

Reads exclusively through `ambo.common.db` (AD-030) -- this script is Python
orchestration over the frozen mart contract, never a second SQL layer. The export
registry (`EXPORT_REGISTRY`) is a dict keyed by output filename (D-03): Phase 8
(`allocation_scenarios.csv`, `attribution_gap.csv`) and Phase 9 (the remaining
SPEC-03 section 5 files) add an entry each, never a second script and never a second
float-formatting path.

D-05 -- the a-euro-in-committed-exports interaction is recorded here, not acted on:
`exports/mmm_input_weekly.csv` is committed by design (SPEC-08 section 2, EB-081)
because Phase 9's DL-1 probe compares regenerated output against it. Once Phase 6
flips `layer_r_present`, this committed export will carry Layer R a-euro rows into
the history of a repository that goes public at M3. Phase 1's D-26 scoped a-euro
figures in `exports/` out of the leak scan, correctly, at a time when nothing was
committed there. The `docs/RISK_REGISTER.md` entry plan 03-09 adds is the tracking
mechanism for this revisit, so it does not depend on anyone's memory.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ambo.common.config import load_settings
from ambo.common.db import read_dim_layer, read_mmm_input
from ambo.common.errors import DataContractError


@dataclass(frozen=True)
class ExportSpec:
    """One export registry entry (D-03).

    `reader` produces the frame to export. `columns` derives the ordered column
    list from that frame itself -- a mart's column order is never restated as a
    literal here (D-08's discipline, applied to this script). `dtype_casts` maps a
    column name to a cast keyword applied immediately before writing: `"date"`
    formats the column as `YYYY-MM-DD`, `"Int64"` casts to the nullable pandas
    integer dtype so an integer never renders with a decimal point and a NULL never
    renders as zero (D-04). `sort_keys` is the ordered column list the frame is
    sorted by, ascending, before writing -- and is also the frame's grain key,
    checked for duplicates before any row is written (AD-050).
    """

    reader: Callable[[], pd.DataFrame]
    columns: Callable[[pd.DataFrame], list[str]]
    dtype_casts: dict[str, str]
    sort_keys: list[str]


def _read_mmm_input_all_layers() -> pd.DataFrame:
    """Concatenate `read_mmm_input(layer)` across every layer `read_dim_layer()`
    reports -- never a hard-coded layer name list, so a future layer (Layer R) is
    picked up automatically once it exists in `dim_layer`, with no change to this
    function."""
    layers = read_dim_layer()["layer"].tolist()
    frames = [read_mmm_input(layer) for layer in layers]
    return pd.concat(frames, ignore_index=True)


# The export registry (D-03): a dict keyed by output filename. Adding a later
# phase's file is adding an entry here, never touching the writing code path below.
EXPORT_REGISTRY: dict[str, ExportSpec] = {
    "mmm_input_weekly.csv": ExportSpec(
        reader=_read_mmm_input_all_layers,
        columns=lambda frame: list(frame.columns),
        dtype_casts={
            "week_start": "date",
            "orders": "Int64",
            "promo_flag": "Int64",
            "advent_flag": "Int64",
            "jan_dip_flag": "Int64",
            "spring_flag": "Int64",
            "schulbeginn_flag": "Int64",
            "summer_lull_flag": "Int64",
        },
        sort_keys=["layer", "week_start"],
    ),
}


def validate_no_duplicate_grain_keys(frame: pd.DataFrame, sort_keys: list[str]) -> None:
    """AD-050's negative-side proof (ROADMAP success criterion 4): a duplicated
    grain key (the `sort_keys` combination) in `frame` raises `DataContractError`
    naming the duplicated key(s) -- never silently deduplicated, never passed
    through to the written file."""
    duplicated_mask = frame.duplicated(subset=sort_keys, keep=False)
    if duplicated_mask.any():
        duplicate_keys = (
            frame.loc[duplicated_mask, sort_keys].drop_duplicates().apply(tuple, axis=1).tolist()
        )
        raise DataContractError(
            f"export validation: duplicate grain key(s) {duplicate_keys} on "
            f"{sort_keys} -- an export never silently deduplicates a grain key."
        )


def _apply_dtype_casts(frame: pd.DataFrame, dtype_casts: dict[str, str]) -> pd.DataFrame:
    frame = frame.copy()
    for column, cast in dtype_casts.items():
        if cast == "date":
            frame[column] = pd.to_datetime(frame[column]).dt.strftime("%Y-%m-%d")
        elif cast == "Int64":
            frame[column] = frame[column].astype("Int64")
        else:
            raise DataContractError(
                f"export: unknown dtype cast {cast!r} for column {column!r} -- "
                "expected 'date' or 'Int64'."
            )
    return frame


def _atomic_write_csv(frame: pd.DataFrame, path: Path) -> None:
    """Byte-stable atomic CSV write (D-02/D-04), mirroring
    `ambo.simulate.__main__._atomic_write_csv` verbatim: a `.tmp-<pid>` sibling
    opened with `newline=""`, a fixed `%.6f` float format, an explicit LF line
    terminator, `na_rep=""` so a NULL renders as a genuinely empty field, and
    `index=False` -- then `os.replace` onto `path`. The temp file is removed on any
    exception, so a crashed export never leaves a half-written committed artifact
    (T-03-35). pandas' default float repr is never used: a minor version bump could
    otherwise rewrite every line of a committed, diff-checked file for a reason
    unrelated to the warehouse (D-04).
    """
    tmp_path = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    try:
        with tmp_path.open("w", encoding="utf-8", newline="") as handle:
            frame.to_csv(
                handle,
                index=False,
                na_rep="",
                float_format="%.6f",
                lineterminator="\n",
            )
            handle.flush()
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def build_export_frame(spec: ExportSpec) -> pd.DataFrame:
    """Read, select the reader's own column order, validate (AD-050: no duplicate
    grain key), and sort `spec`'s frame -- everything `write_export` does short of
    the dtype casts and the actual write, factored out so a test can inspect the
    frame independently of file I/O."""
    frame = spec.reader()
    frame = frame.reindex(columns=spec.columns(frame))
    validate_no_duplicate_grain_keys(frame, spec.sort_keys)
    return frame.sort_values(by=spec.sort_keys, kind="mergesort").reset_index(drop=True)


def write_export(name: str, outdir: Path) -> Path:
    """Write registry entry `name` to `<outdir>/<name>`, returning the written
    path. Pipeline: read -> select column order -> validate (AD-050) -> sort ->
    cast dtypes -> atomic write (D-02/D-04)."""
    spec = EXPORT_REGISTRY[name]
    frame = build_export_frame(spec)
    frame = _apply_dtype_casts(frame, spec.dtype_casts)
    path = outdir / name
    _atomic_write_csv(frame, path)
    return path


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: `python scripts/export_marts.py [NAME ...]`. With no
    arguments, writes every registry entry; with one or more names, writes only
    those (a later phase can regenerate one file without rebuilding the rest).
    Returns 0 on success. Resolves the output directory through
    `load_settings().paths.exports` -- never a hard-coded path."""
    parser = argparse.ArgumentParser(
        prog="export_marts.py",
        description=(
            "Write one or more export registry entries (T-205, D-03) from the "
            "warehouse marts to exports/*.csv, byte-stably (D-02/D-04) through "
            "the AD-030 doorway (ambo.common.db)."
        ),
    )
    parser.add_argument(
        "names",
        nargs="*",
        help=(
            "Which registry entries to write, by output filename (default: all "
            f"of them -- currently {sorted(EXPORT_REGISTRY)})."
        ),
    )
    args = parser.parse_args(argv)

    names = args.names if args.names else sorted(EXPORT_REGISTRY)
    unknown = [name for name in names if name not in EXPORT_REGISTRY]
    if unknown:
        parser.error(
            f"unknown export registry entr{'y' if len(unknown) == 1 else 'ies'} "
            f"{unknown} -- valid names are {sorted(EXPORT_REGISTRY)}."
        )

    outdir = load_settings().paths.exports
    outdir.mkdir(parents=True, exist_ok=True)

    for name in names:
        path = write_export(name, outdir)
        print(f"wrote {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
