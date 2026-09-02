"""The simulator CLI and the SIM-070...075 + BP-G-02 gate runner (SPEC-01 section 1,
SIM-004, section 7; T-108).

Implements: REQ-q1-truth-recovery, REQ-grain-and-windows

This is the only module in `simulate/` that performs I/O (Functional-Core /
Imperative-Shell): `config.py`, `dgp.py`, `spend_patterns.py`, `platform_bias.py` and
`truth.py`'s pure functions stay independently testable, and this module is the sole
place that reads a scenario's assembled result and writes it to disk. Uses
`get_logger(__name__)` for all progress and gate output -- never `print`, per
`common/logging.py`'s stated invariant.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

from ambo.common.config import repo_root
from ambo.common.errors import SimulationError
from ambo.common.logging import get_logger
from ambo.simulate.config import SPEC_CHANNEL_ORDER, ScenarioConfig, load_scenario
from ambo.simulate.dgp import (
    SimulationResult,
    adstock_recursive,
    assemble_scenario,
    decomposition_audit,
    hill,
    peak_week_audit,
    plausibility_audit,
)
from ambo.simulate.platform_bias import platform_report
from ambo.simulate.truth import TruthFile, compute_truth, write_truth

logger = get_logger(__name__)

# The three SPEC-01 section 5 scenario ids, in this fixed generation order -- never
# reordered, matching every other module in this package.
_SCENARIO_NAMES: tuple[str, ...] = ("s_a", "s_b", "s_c")
_TARGET_CHOICES: tuple[str, ...] = ("all", *_SCENARIO_NAMES, "validate")

# SIM-004's exact column names and order, for both written CSVs.
_MEDIA_COLUMNS: tuple[str, ...] = (
    "week_start",
    "channel",
    "spend_eur",
    "impressions",
    "platform_conversions",
    "platform_revenue_eur",
)
_OUTCOME_COLUMNS: tuple[str, ...] = ("week_start", "revenue_eur", "orders", "promo_flag")

# The nine SIM-004 artifacts, in a fixed order -- what `_gate_sim_070` hashes and what
# every non-vacuous existence check below iterates.
_ARTIFACT_NAMES: tuple[str, ...] = ("media_weekly.csv", "outcome_weekly.csv", "truth.json")
_EXPECTED_RELATIVE_PATHS: tuple[str, ...] = tuple(
    f"{name}/{artifact}" for name in _SCENARIO_NAMES for artifact in _ARTIFACT_NAMES
)

# BP-G-02's real home is SIM-002's single-home YAML-vs-SPEC-01-section-4 check in
# tests/unit/test_scenario_config.py -- this string names the selector without
# spelling out the test-runner's own name, since this module must import nothing
# from it (T-108 Task 2 acceptance criterion).
_BP_G_02_SELECTOR = 'tests/unit/test_scenario_config.py -k "spec_parameter_table or rule_level"'


def _atomic_write_csv(frame: pd.DataFrame, path: Path) -> None:
    """Write `frame` to `path` atomically (EB-050), mirroring `truth.write_truth`'s
    `.tmp-<pid>` sibling / `os.replace` pattern: UTF-8, LF-only (`newline=""` on open
    plus an explicit `lineterminator="\\n"`, so the writer pins the line ending itself
    rather than relying on `.gitattributes` -- CI's diff check runs before git's
    checkout filters), a fixed `%.6f` float format, `na_rep=""` so a NULL renders as a
    genuinely empty field, and `index=False`. The temp file is removed on any
    exception so an interrupted write never leaves debris or a partially-written
    original.
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


def _write_media_csv(media: pd.DataFrame, path: Path) -> None:
    """Write `media` (the platform-completed SIM-004 long frame) to `path`,
    byte-stable by construction. `week_start` is formatted as `YYYY-MM-DD`;
    `spend_eur`, `impressions` and `platform_conversions` are cast to the nullable
    `Int64` dtype so they render with no decimal point and an offline channel's
    NULL survives as an empty field (never `0`); `platform_revenue_eur` is cast to
    plain `float64` so `_atomic_write_csv`'s `%.6f` format applies and a missing
    value renders as an empty field via `na_rep`.
    """
    frame = media.reindex(columns=list(_MEDIA_COLUMNS)).copy()
    frame["week_start"] = pd.to_datetime(frame["week_start"]).dt.strftime("%Y-%m-%d")
    frame["spend_eur"] = frame["spend_eur"].astype("Int64")
    frame["impressions"] = frame["impressions"].astype("Int64")
    frame["platform_conversions"] = frame["platform_conversions"].astype("Int64")
    frame["platform_revenue_eur"] = frame["platform_revenue_eur"].astype("float64")
    _atomic_write_csv(frame, path)


def _write_outcome_csv(outcome: pd.DataFrame, path: Path) -> None:
    """Write `outcome` (the SIM-004 `outcome_weekly.csv` frame) to `path`,
    byte-stable by construction, mirroring `_write_media_csv`'s dtype discipline:
    `week_start` as `YYYY-MM-DD`, `orders`/`promo_flag` cast to nullable `Int64` so
    they render with no decimal point, `revenue_eur` cast to plain `float64` so the
    `%.6f` format applies.
    """
    frame = outcome.reindex(columns=list(_OUTCOME_COLUMNS)).copy()
    frame["week_start"] = pd.to_datetime(frame["week_start"]).dt.strftime("%Y-%m-%d")
    frame["revenue_eur"] = frame["revenue_eur"].astype("float64")
    frame["orders"] = frame["orders"].astype("Int64")
    frame["promo_flag"] = frame["promo_flag"].astype("Int64")
    _atomic_write_csv(frame, path)


def _generate_scenario(name: str, outdir: Path) -> None:
    """Assemble scenario `name` and write its three SIM-004 artifacts under
    `<outdir>/<name>/`. The single per-scenario pipeline both `main`'s generation
    targets and `_gate_sim_070`'s SIM-070 regeneration call, so the two can never
    independently drift out of sync. `rng` is a fresh `np.random.default_rng(cfg.seed)`
    -- never reused across scenarios (SIM-001/SIM-070 determinism).
    """
    cfg = load_scenario(name)
    rng = np.random.default_rng(cfg.seed)
    result = assemble_scenario(cfg, rng)
    media = platform_report(result)
    truth = compute_truth(result, media)

    scenario_dir = outdir / name
    scenario_dir.mkdir(parents=True, exist_ok=True)
    _write_media_csv(media, scenario_dir / "media_weekly.csv")
    _write_outcome_csv(result.outcome, scenario_dir / "outcome_weekly.csv")
    write_truth(truth, scenario_dir / "truth.json")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point (T-108): `python -m ambo.simulate {all|s_a|s_b|s_c|validate}
    [--outdir PATH]`.

    For `all`/`s_a`/`s_b`/`s_c`, generates the requested scenario(s) -- `all` in the
    fixed order `s_a, s_b, s_c` -- writing `media_weekly.csv`, `outcome_weekly.csv`
    and `truth.json` under `<outdir>/<scenario>/`. For `validate`, delegates to
    `validate_sim(outdir)`. Returns 0 on success, 1 on a `SimulationError` (message
    logged). An unrecognised `target` is rejected by `argparse` itself, which exits 2
    with a usage message naming the five valid choices -- since argument parsing
    completes (and therefore any exit-2 failure happens) before any directory is
    created, an unknown target never leaves a partial output tree. `--outdir` defaults
    to `repo_root() / "data" / "synthetic"`.
    """
    parser = argparse.ArgumentParser(prog="python -m ambo.simulate")
    parser.add_argument("target", choices=_TARGET_CHOICES)
    parser.add_argument("--outdir", type=Path, default=None)
    args = parser.parse_args(argv)

    outdir: Path = args.outdir if args.outdir is not None else repo_root() / "data" / "synthetic"

    if args.target == "validate":
        return validate_sim(outdir)

    scenario_names = _SCENARIO_NAMES if args.target == "all" else (args.target,)

    try:
        for name in scenario_names:
            start = time.monotonic()
            _generate_scenario(name, outdir)
            elapsed = time.monotonic() - start
            logger.info("scenario %s written to %s in %.2fs", name, outdir / name, elapsed)
    except SimulationError as exc:
        logger.error("%s", exc)
        return 1

    return 0


def _hash_tree(root: Path, relative_paths: tuple[str, ...]) -> tuple[str, list[str]]:
    """Return `(sha256_hex, missing_or_empty)` for `relative_paths` under `root`.

    `missing_or_empty` names every relative path that is absent or has zero size,
    checked **before** any hashing -- a partial or empty regeneration is reported by
    file name, not folded silently into a hash mismatch (mirroring
    `tests/unit/test_import_independence.py`'s own non-vacuous-scan discipline).
    When `missing_or_empty` is empty, `sha256_hex` is the digest of the files' bytes
    concatenated in `relative_paths`'s fixed order.
    """
    problems: list[str] = []
    for rel in relative_paths:
        path = root / rel
        if not path.is_file() or path.stat().st_size == 0:
            problems.append(rel)
    if problems:
        return "", problems

    digest = hashlib.sha256()
    for rel in relative_paths:
        digest.update((root / rel).read_bytes())
    return digest.hexdigest(), []


def _gate_sim_070(outdir: Path) -> tuple[bool, str]:
    """SIM-070: regenerate all three scenarios into a fresh temporary directory and
    byte-compare (via SHA-256 over the fixed nine-file order) against `outdir` --
    catching both a non-deterministic implementation and an accidental hand-edit of
    a committed artifact. Evidence is the two hashes printed as a pair.
    """
    committed_hash, committed_problems = _hash_tree(outdir, _EXPECTED_RELATIVE_PATHS)
    if committed_problems:
        return False, f"missing or empty file(s) in the committed tree: {committed_problems}"

    with tempfile.TemporaryDirectory(prefix="ambo-simulate-validate-") as tmp:
        regen_root = Path(tmp)
        for name in _SCENARIO_NAMES:
            _generate_scenario(name, regen_root)
        regen_hash, regen_problems = _hash_tree(regen_root, _EXPECTED_RELATIVE_PATHS)

    if regen_problems:
        return False, f"missing or empty file(s) in the regenerated tree: {regen_problems}"

    passed = committed_hash == regen_hash
    return passed, f"committed={committed_hash} regenerated={regen_hash}"


def _gate_sim_071(results: dict[str, SimulationResult]) -> tuple[bool, str]:
    """SIM-071: the maximum absolute decomposition deviation across all three
    scenarios, from `dgp.decomposition_audit`. Passes when `<= 1e-6`.
    """
    deviations = {name: decomposition_audit(result) for name, result in results.items()}
    max_deviation = max(deviations.values())
    passed = max_deviation <= 1e-6
    per_scenario = ", ".join(f"{name}={value!r}" for name, value in deviations.items())
    return passed, f"{per_scenario} (max={max_deviation!r}, bound<=1e-6)"


def _gate_sim_072(results: dict[str, SimulationResult]) -> tuple[bool, str]:
    """SIM-072: per-scenario plausibility statistics from `dgp.plausibility_audit`.
    Passes when every scenario's `min_revenue_pre_clip >= 0`, every
    `media_share_<iso_year>` is in `[0.15, 0.45]`, and `noise_variance_share` is in
    `[0.02, 0.10]`.
    """
    problems: list[str] = []
    summaries: list[str] = []
    for name, result in results.items():
        stats = plausibility_audit(result)
        summaries.append(f"{name}: {stats}")

        if stats["min_revenue_pre_clip"] < 0.0:
            problems.append(f"{name}: min_revenue_pre_clip={stats['min_revenue_pre_clip']!r} < 0")

        noise_share = stats["noise_variance_share"]
        if not (0.02 <= noise_share <= 0.10):
            problems.append(f"{name}: noise_variance_share={noise_share!r} outside [0.02, 0.10]")

        for key, value in stats.items():
            if key.startswith("media_share_") and not (0.15 <= value <= 0.45):
                problems.append(f"{name}: {key}={value!r} outside [0.15, 0.45]")

    evidence = "; ".join(summaries)
    if problems:
        evidence += " -- FAILING: " + "; ".join(problems)
    return not problems, evidence


def _gate_sim_073(results: dict[str, SimulationResult]) -> tuple[bool, str]:
    """SIM-073: per covered ISO year, the peak-revenue week and its Advent flag, from
    `dgp.peak_week_audit`. Passes when every *audited* year's boolean is `True`; a
    skipped year (the documented `(-1, True)` sentinel) is reported by name, never
    silently omitted.
    """
    passed = True
    notes: list[str] = []
    for name, result in results.items():
        for iso_year, (peak_week, is_advent) in sorted(peak_week_audit(result).items()):
            if peak_week == -1:
                notes.append(f"{name} {iso_year}: skipped (Advent window not fully covered)")
                continue
            notes.append(f"{name} {iso_year}: peak_week={peak_week} advent_flag={is_advent}")
            if not is_advent:
                passed = False
    return passed, "; ".join(notes)


def _gate_sim_074(configs: dict[str, ScenarioConfig]) -> tuple[bool, str]:
    """SIM-074: three closed-form checks, evaluated in-process against
    `dgp.adstock_recursive`/`dgp.hill` directly -- never by shelling out, since
    `src/` must not depend on the test framework. Over every distinct `lam` value and
    every distinct `(K, s)` pair the loaded scenario configs declare: (1) the
    constant-spend limit at t=200 agrees with the closed form `x / (1 - lam)` within
    1e-9; (2) the impulse response `a_t == lam**t` agrees within 1e-9 (the check the
    project's own trap-T-2 discipline names -- a reversed convolution passes the
    constant-spend limit but fails this one); (3) `hill(K, K, s) == 0.5` agrees within
    1e-12.
    """
    lam_values: set[float] = set()
    ks_pairs: set[tuple[float, float]] = set()
    for cfg in configs.values():
        for channel_id in SPEC_CHANNEL_ORDER:
            params = cfg.channels[channel_id].true_params
            lam_values.add(params.lam)
            ks_pairs.add((params.K, params.s))

    constant_spend_residual = 0.0
    for lam in lam_values:
        x = np.full(200, 1000.0)
        a = adstock_recursive(x, lam)
        expected_limit = 1000.0 / (1.0 - lam)
        constant_spend_residual = max(constant_spend_residual, abs(float(a[-1]) - expected_limit))

    impulse_residual = 0.0
    for lam in lam_values:
        x = np.zeros(50)
        x[0] = 1.0
        a = adstock_recursive(x, lam)
        expected_impulse = lam ** np.arange(50)
        impulse_residual = max(impulse_residual, float(np.max(np.abs(a - expected_impulse))))

    hill_residual = 0.0
    for K, s in ks_pairs:
        value = float(hill(np.array([K]), K, s)[0])
        hill_residual = max(hill_residual, abs(value - 0.5))

    passed = constant_spend_residual <= 1e-9 and impulse_residual <= 1e-9 and hill_residual <= 1e-12
    evidence = (
        f"constant_spend_residual={constant_spend_residual!r} (bound<=1e-9), "
        f"impulse_residual={impulse_residual!r} (bound<=1e-9), "
        f"hill_at_K_residual={hill_residual!r} (bound<=1e-12)"
    )
    return passed, evidence


def _gate_sim_075(outdir: Path, configs: dict[str, ScenarioConfig]) -> tuple[bool, str]:
    """SIM-075: re-read each written `truth.json` from disk, re-validate it against
    `TruthFile`, and assert every SPEC-01 section 4 (`lam`, `K`, `s`, `beta`) and
    section 6 (`platform_phi`, `platform_theta`, `platform_cpm`) parameter equals the
    corresponding loaded `ScenarioConfig` value.
    """
    problems: list[str] = []
    for name in _SCENARIO_NAMES:
        truth_path = outdir / name / "truth.json"
        try:
            truth = TruthFile.model_validate_json(truth_path.read_text(encoding="utf-8"))
        except Exception as exc:
            problems.append(f"{name}: failed to load/validate {truth_path}: {exc!r}")
            continue

        cfg = configs[name]
        for channel_id, channel_truth in zip(SPEC_CHANNEL_ORDER, truth.channels, strict=True):
            params = cfg.channels[channel_id].true_params
            if (channel_truth.lam, channel_truth.K, channel_truth.s, channel_truth.beta) != (
                params.lam,
                params.K,
                params.s,
                params.beta,
            ):
                problems.append(f"{name}/{channel_id}: section 4 parameter mismatch")

            platform = cfg.channels[channel_id].platform
            if (
                channel_truth.platform_phi,
                channel_truth.platform_theta,
                channel_truth.platform_cpm,
            ) != (platform.phi, platform.theta, platform.cpm):
                problems.append(f"{name}/{channel_id}: section 6 parameter mismatch")

    passed = not problems
    evidence = (
        "all three truth.json files re-validated and match ScenarioConfig"
        if passed
        else "; ".join(problems)
    )
    return passed, evidence


def validate_sim(outdir: Path) -> int:
    """SIM-070...075 + BP-G-02 gate runner (T-108, 10_VALIDATION_GATES.md section 3).

    Evaluates six PASS/FAIL rows -- SIM-070 determinism, SIM-071 decomposition,
    SIM-072 plausibility, SIM-073 seasonality, SIM-074 closed forms, SIM-075 truth
    completeness -- plus a seventh `DELEGATED` row naming BP-G-02's real home (SIM-002's
    single-home YAML-vs-SPEC-01-section-4 check, which lives in
    `tests/unit/test_scenario_config.py`, not here): `make validate-sim` runs that
    selector in the same invocation as this function, so the target as a whole cannot
    go green without it, even though this function's own exit code reflects only the
    six rows it can evaluate in-process.

    Logs a fixed-width `GATE | STATUS | EVIDENCE` table and returns 0 if and only if
    every SIM-0xx row is `PASS`. Performs no remediation on a red gate (ROADMAP Phase 2
    rollback rule, 10_VALIDATION_GATES.md section 3's failure protocol): a red gate is
    an implementation bug until proven otherwise, and widening a bound is never done
    here.
    """
    configs = {name: load_scenario(name) for name in _SCENARIO_NAMES}
    results = {
        name: assemble_scenario(configs[name], np.random.default_rng(configs[name].seed))
        for name in _SCENARIO_NAMES
    }

    rows: list[tuple[str, str, str]] = []

    passed_070, evidence_070 = _gate_sim_070(outdir)
    rows.append(("SIM-070", "PASS" if passed_070 else "FAIL", evidence_070))

    passed_071, evidence_071 = _gate_sim_071(results)
    rows.append(("SIM-071", "PASS" if passed_071 else "FAIL", evidence_071))

    passed_072, evidence_072 = _gate_sim_072(results)
    rows.append(("SIM-072", "PASS" if passed_072 else "FAIL", evidence_072))

    passed_073, evidence_073 = _gate_sim_073(results)
    rows.append(("SIM-073", "PASS" if passed_073 else "FAIL", evidence_073))

    passed_074, evidence_074 = _gate_sim_074(configs)
    rows.append(("SIM-074", "PASS" if passed_074 else "FAIL", evidence_074))

    passed_075, evidence_075 = _gate_sim_075(outdir, configs)
    rows.append(("SIM-075", "PASS" if passed_075 else "FAIL", evidence_075))

    rows.append(
        (
            "BP-G-02",
            "DELEGATED",
            "scenario YAML == SPEC-01 section 4 table (SIM-002 single home); checked "
            f"by the selector `{_BP_G_02_SELECTOR}`, run by make validate-sim in the "
            "same invocation so the target cannot go green without it.",
        )
    )

    logger.info("%-8s %-10s %s", "GATE", "STATUS", "EVIDENCE")
    for gate_id, status, evidence in rows:
        logger.info("%-8s %-10s %s", gate_id, status, evidence)

    sim_rows = rows[:-1]
    all_passed = all(status == "PASS" for _, status, _ in sim_rows)
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
