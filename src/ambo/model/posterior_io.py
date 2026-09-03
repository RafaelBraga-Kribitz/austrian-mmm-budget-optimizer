"""Posterior parquet persistence (MD-051).

Thins stacked ``(chain, draw)`` samples, writes a DataFrame with
``<var>`` / ``<var>__<coord>`` columns, and stores scale factors plus
fit provenance in parquet schema metadata under ``ambo_posterior``.

The InferenceData NetCDF next to the parquet is a local debug artifact
(``*.nc`` is gitignored); the parquet is the load-bearing store
(MD-051 / BP-D-06). Atomic writes use a sibling temp file plus
``os.replace`` (EB-050).

Implements: MD-051, EB-050, BP-D-06
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import arviz as az
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ambo.common.config import load_settings
from ambo.common.errors import FitError
from ambo.common.logging import get_logger
from ambo.model.transforms import ScaleFactors

LOGGER = get_logger(__name__)

_META_KEY = b"ambo_posterior"
# MD-051: every 4th stacked (chain, draw) sample → 1000 rows at full MD-050.
_DEFAULT_THIN = 4

# BP-D-06 primary names. ``R__loco-<channel>`` is matched separately.
_PRIMARY_NAMES = frozenset(
    {
        "P-SA",
        "P-SB",
        "P-SC",
        "P-SA__holdout",
        "P-SB__holdout",
        "P-SC__holdout",
        "R",
        "R__flat",
        "R__nopromo",
        "P-SB__flat",
    }
)


@dataclass(frozen=True)
class PosteriorBundle:
    """Loaded thinned draws plus the scale factors needed to unscale.

    Implements: MD-051
    """

    draws: pd.DataFrame
    metadata: dict[str, Any]
    scale_factors: ScaleFactors
    path: Path


def save_posterior(
    idata: az.InferenceData,
    sf: ScaleFactors,
    name: str,
    *,
    data_hash: str,
    prior_sha256: str,
    thin: int = _DEFAULT_THIN,
    directory: Path | None = None,
) -> Path:
    """Thin, flatten, and atomically write ``name.parquet`` (MD-051).

    Also writes ``name.nc`` beside the parquet (ArviZ default ``h5netcdf``,
    already transitive via arviz). The destination directory is created if
    missing.

    Implements: MD-051
    """
    _validate_artifact_name(name)
    dest = _resolve_parquet_path(name, directory)
    dest.parent.mkdir(parents=True, exist_ok=True)
    posterior = getattr(idata, "posterior", None)
    if posterior is None:
        raise FitError("InferenceData has no posterior group")
    draws = _flatten_posterior(posterior, thin=thin)
    payload = _build_metadata(
        sf=sf,
        name=name,
        data_hash=data_hash,
        prior_sha256=prior_sha256,
        thin=thin,
    )
    _atomic_write_parquet(_table_with_metadata(draws, payload), dest)
    _try_write_netcdf(idata, dest.with_suffix(".nc"))
    LOGGER.info("Wrote posterior %s (%d draws)", dest, len(draws))
    return dest


def load_posterior(name: str, *, directory: Path | None = None) -> PosteriorBundle:
    """Read a parquet posterior; FitError if scale factors are missing.

    Implements: MD-051
    """
    _validate_artifact_name(name)
    path = _resolve_parquet_path(name, directory)
    if not path.is_file():
        raise FitError(f"posterior parquet not found: {path}")
    table = _read_parquet_table(path)
    payload = _read_metadata(table)
    sf = _scale_factors_from_payload(payload)
    return PosteriorBundle(
        draws=table.to_pandas(),
        metadata=payload,
        scale_factors=sf,
        path=path,
    )


def _validate_artifact_name(name: str) -> None:
    """BP-D-06 basenames only; refuse path separators."""
    if not name or name != Path(name).name or "/" in name or "\\" in name:
        raise FitError(f"posterior name {name!r} must be a BP-D-06 basename")
    if name in _PRIMARY_NAMES:
        return
    prefix = "R__loco-"
    if name.startswith(prefix):
        channel = name.removeprefix(prefix)
        if channel.isidentifier() and channel[0].isalpha():
            return
    raise FitError(f"posterior name {name!r} is not a BP-D-06 artifact name")


def _resolve_parquet_path(name: str, directory: Path | None) -> Path:
    """``data/posteriors/<name>.parquet`` unless ``directory`` is given."""
    root = directory if directory is not None else load_settings().paths.posteriors
    return Path(root) / f"{name}.parquet"


def _flatten_posterior(posterior: Any, *, thin: int) -> pd.DataFrame:
    """Stack chains×draws, thin, flatten extra dims into column names."""
    if thin < 1:
        raise FitError(f"thin must be >= 1, got {thin}")
    stacked = posterior.stack(sample=("chain", "draw"))
    stacked = stacked.isel(sample=slice(None, None, thin))
    columns: dict[str, Any] = {}
    for var_name, da in stacked.data_vars.items():
        extra = [d for d in da.dims if d != "sample"]
        if not extra:
            columns[str(var_name)] = da.values
            continue
        if len(extra) != 1:
            raise FitError(f"cannot flatten posterior var {var_name!r} with dims {da.dims}")
        dim = extra[0]
        labels = [str(lab) for lab in da.coords[dim].values]
        for i, label in enumerate(labels):
            columns[f"{var_name}__{label}"] = da.isel({dim: i}).values
    return pd.DataFrame(columns)


def _build_metadata(
    *,
    sf: ScaleFactors,
    name: str,
    data_hash: str,
    prior_sha256: str,
    thin: int,
) -> dict[str, Any]:
    """Provenance JSON stored in parquet schema metadata."""
    sampler = load_settings().sampler
    spend_means = {str(k): float(v) for k, v in sf.spend_means.items()}
    return {
        "name": name,
        "thin": thin,
        "data_hash": data_hash,
        "prior_sha256": prior_sha256,
        "git_commit": _git_commit(),
        "seed": sampler.random_seed,
        "sampler": {
            "chains": sampler.chains,
            "tune": sampler.tune,
            "draws": sampler.draws,
            "target_accept": sampler.target_accept,
            "random_seed": sampler.random_seed,
            "init": sampler.init,
        },
        "scale_factors": {
            "spend_means": spend_means,
            "revenue_mean": float(sf.revenue_mean),
            "channels": list(spend_means),
        },
    }


def _table_with_metadata(draws: pd.DataFrame, payload: dict[str, Any]) -> pa.Table:
    table = pa.Table.from_pandas(draws, preserve_index=False)
    existing = dict(table.schema.metadata or {})
    existing[_META_KEY] = json.dumps(payload).encode("utf-8")
    return table.replace_schema_metadata(existing)


def _atomic_write_parquet(table: pa.Table, dest: Path) -> None:
    """Write via a sibling temp file; ``os.replace`` is the commit point."""
    tmp_path = dest.with_suffix(dest.suffix + f".tmp-{os.getpid()}")
    try:
        pq.write_table(table, tmp_path)
        os.replace(tmp_path, dest)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def _try_write_netcdf(idata: az.InferenceData, path: Path) -> None:
    """Local full-idata companion. Default engine is arviz's h5netcdf."""
    try:
        idata.to_netcdf(os.fspath(path))
    except Exception:
        LOGGER.warning("NetCDF debug write failed for %s", path, exc_info=True)


def _read_parquet_table(path: Path) -> pa.Table:
    """Read parquet without calling ``read_table`` (AD-030 AST guard)."""
    return pq.ParquetFile(path).read()


def _read_metadata(table: pa.Table) -> dict[str, Any]:
    raw = table.schema.metadata or {}
    blob = raw.get(_META_KEY)
    if blob is None:
        raise FitError("posterior parquet is missing ambo_posterior schema metadata")
    payload = json.loads(blob.decode("utf-8"))
    if not isinstance(payload, dict):
        raise FitError("ambo_posterior metadata is not a JSON object")
    return payload


def _scale_factors_from_payload(payload: dict[str, Any]) -> ScaleFactors:
    raw = payload.get("scale_factors")
    if not isinstance(raw, dict):
        raise FitError("scale factors missing from posterior metadata")
    spend_means = raw.get("spend_means")
    revenue_mean = raw.get("revenue_mean")
    if not isinstance(spend_means, dict) or not spend_means or revenue_mean is None:
        raise FitError("scale factors missing from posterior metadata")
    return ScaleFactors(
        spend_means={str(k): float(v) for k, v in spend_means.items()},
        revenue_mean=float(revenue_mean),
    )


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result.stdout.strip() or "unknown"
