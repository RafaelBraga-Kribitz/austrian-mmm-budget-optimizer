"""The Bayesian marketing mix model, one definition for every layer.

Structure, on scaled data (revenue divided by its training mean, each channel's
spend divided by the mean of its positive-spend training weeks)::

    mu[t] = intercept
          + trend * t / T_train
          + sum_j seasonality_sin[j] sin(2 pi j t / period) + seasonality_cos[j] cos(...)
          + control * control[t]
          + sum_c effect[c] * Hill(adstock(spend[:, c]; decay[c]); half_saturation[c], slope[c])
    revenue[t] ~ Normal(mu[t], noise)

Everything that reports a number recomputes it in numpy from the posterior draws
with ``ambo.transforms``; the pytensor graph and the numpy reference are tested
against each other.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import arviz as az
import numpy as np
import pandas as pd
import pymc as pm
import pytensor.tensor as pt

from ambo import diagnostics
from ambo.transforms import adstock, adstock_pt, hill, hill_pt

PARAM_NAMES = (
    "intercept",
    "trend",
    "seasonality_sin",
    "seasonality_cos",
    "control",
    "decay",
    "half_saturation",
    "slope",
    "effect",
    "noise",
)


@dataclass
class ModelData:
    """A weekly dataset prepared for the model, with its scaling remembered."""

    channels: list[str]
    weeks: np.ndarray  # 1-based week index, length T
    spend: np.ndarray  # (T, C) in money units
    revenue: np.ndarray  # (T,) in money units
    control: np.ndarray  # (T,)
    spend_means: np.ndarray  # (C,) mean of positive-spend training weeks
    revenue_mean: float
    n_train: int  # divisor of the trend term
    adstock_length: int
    fourier_order: int
    fourier_period: float
    control_name: str = "control"
    week_start: list[str] = field(default_factory=list)

    @property
    def n_weeks(self) -> int:
        return int(len(self.weeks))

    @property
    def spend_scaled(self) -> np.ndarray:
        return self.spend / self.spend_means[None, :]

    @property
    def revenue_scaled(self) -> np.ndarray:
        return self.revenue / self.revenue_mean

    @property
    def trend_feature(self) -> np.ndarray:
        return self.weeks.astype(float) / float(self.n_train)

    def fourier_features(self) -> tuple[np.ndarray, np.ndarray]:
        t = self.weeks.astype(float)
        orders = np.arange(1, self.fourier_order + 1, dtype=float)
        angle = 2.0 * np.pi * np.outer(t, orders) / self.fourier_period
        return np.sin(angle), np.cos(angle)

    def slice(self, start: int, stop: int) -> ModelData:
        """Rows ``start:stop`` with the same scaling and trend divisor."""
        return ModelData(
            channels=self.channels,
            weeks=self.weeks[start:stop],
            spend=self.spend[start:stop],
            revenue=self.revenue[start:stop],
            control=self.control[start:stop],
            spend_means=self.spend_means,
            revenue_mean=self.revenue_mean,
            n_train=self.n_train,
            adstock_length=self.adstock_length,
            fourier_order=self.fourier_order,
            fourier_period=self.fourier_period,
            control_name=self.control_name,
            week_start=self.week_start[start:stop],
        )


def prepare(
    data: pd.DataFrame, config: dict, train_weeks: int | None = None
) -> ModelData:
    """Build ``ModelData`` from a frame with ``spend_<channel>``, ``revenue`` and the control.

    Scaling constants come from the first ``train_weeks`` rows (all rows when None),
    so a holdout fit and its out-of-sample prediction share one scale.
    """
    channels = list(config["channels"])
    control_col = config["control"]["column"]
    n = len(data)
    n_train = int(train_weeks) if train_weeks else n
    if n_train > n or n_train < 1:
        raise ValueError("train_weeks must be between 1 and the number of rows")
    spend = np.column_stack([data[f"spend_{c}"].to_numpy(dtype=float) for c in channels])
    revenue = data["revenue"].to_numpy(dtype=float)
    control = data[control_col].to_numpy(dtype=float)
    train_spend = spend[:n_train]
    means = np.array(
        [
            train_spend[:, i][train_spend[:, i] > 0].mean()
            if (train_spend[:, i] > 0).any()
            else 1.0
            for i in range(len(channels))
        ]
    )
    if "week" in data.columns:
        weeks = data["week"].to_numpy(dtype=int)
    else:
        weeks = np.arange(1, n + 1)
    model_cfg = config["model"]
    return ModelData(
        channels=channels,
        weeks=weeks,
        spend=spend,
        revenue=revenue,
        control=control,
        spend_means=means,
        revenue_mean=float(revenue[:n_train].mean()),
        n_train=n_train,
        adstock_length=int(model_cfg["adstock_length"]),
        fourier_order=int(model_cfg["fourier_order"]),
        fourier_period=float(model_cfg["fourier_period"]),
        control_name=config["control"]["name"],
        week_start=[str(v) for v in data["week_start"]] if "week_start" in data else [],
    )


def _prior(name: str, spec: dict, **kwargs):
    dist = spec["dist"]
    if dist == "normal":
        return pm.Normal(name, mu=float(spec["mu"]), sigma=float(spec["sigma"]), **kwargs)
    if dist == "halfnormal":
        return pm.HalfNormal(name, sigma=float(spec["sigma"]), **kwargs)
    if dist == "beta":
        return pm.Beta(name, alpha=float(spec["a"]), beta=float(spec["b"]), **kwargs)
    if dist == "gamma":
        return pm.Gamma(name, alpha=float(spec["shape"]), beta=float(spec["rate"]), **kwargs)
    if dist == "lognormal":
        return pm.LogNormal(name, mu=float(spec["mu"]), sigma=float(spec["sigma"]), **kwargs)
    raise ValueError(f"unknown prior family {dist!r} for {name}")


def build_model(md: ModelData, priors: dict) -> pm.Model:
    """PyMC model on the scaled data of ``md``.

    Priors (all on scaled units, all channel-agnostic) and the reasoning behind them:

    * ``decay`` Beta(2, 3): carry-over between weeks. Mean 0.4, most mass between
      0.1 and 0.75; rules out decay near 1 (an effect that never fades is not
      identifiable from weekly data) without preferring any channel.
    * ``half_saturation`` Gamma(2, 1): the adstocked spend, as a multiple of the
      channel's average weekly spend, at which the response is at half its maximum.
      Mean 2 and a long right tail: saturation may sit anywhere from well below
      typical spend to far above it, where the curve is effectively linear.
    * ``slope`` LogNormal(0, 0.5): Hill shape. Centred on 1 (Michaelis-Menten), 90
      percent between 0.44 and 2.3, so both concave and S-shaped responses are
      allowed and slopes beyond 3 are not.
    * ``effect`` HalfNormal(0.3): contribution at full saturation as a share of
      average weekly revenue. Positive by construction (advertising does not
      destroy revenue in this model); 90 percent below 0.5, so no single channel is
      expected a priori to add half of average revenue.
    * ``intercept`` Normal(1, 0.5): baseline revenue as a share of the mean. Centred
      on 1 with a wide spread, because the media share is unknown before fitting.
    * ``trend`` Normal(0, 0.3): drift over the training window as a share of mean
      revenue, symmetric because growth and decline are equally plausible.
    * ``seasonality`` Normal(0, 0.2) per Fourier coefficient: seasonal swings of a
      few tens of percent are common in retail; the prior allows them without
      forcing them.
    * ``control`` Normal(0, 0.2): effect of the control indicator as a share of mean
      revenue, symmetric.
    * ``noise`` HalfNormal(0.1): residual standard deviation as a share of mean
      revenue; a weekly fit that misses by more than a third of revenue would be a
      broken model, not noise.
    """
    sin_feat, cos_feat = md.fourier_features()
    trend_feature = md.trend_feature
    coords = {
        "channel": list(md.channels),
        "fourier": list(range(1, md.fourier_order + 1)),
        "week": list(range(md.n_weeks)),
    }
    with pm.Model(coords=coords) as model:
        spend = pm.Data("spend_scaled", md.spend_scaled, dims=("week", "channel"))
        intercept = _prior("intercept", priors["intercept"])
        trend = _prior("trend", priors["trend"])
        seas_sin = _prior("seasonality_sin", priors["seasonality"], dims="fourier")
        seas_cos = _prior("seasonality_cos", priors["seasonality"], dims="fourier")
        control = _prior("control", priors["control"])
        decay = _prior("decay", priors["decay"], dims="channel")
        half_sat = _prior("half_saturation", priors["half_saturation"], dims="channel")
        slope = _prior("slope", priors["slope"], dims="channel")
        effect = _prior("effect", priors["effect"], dims="channel")
        noise = _prior("noise", priors["noise"])

        media_terms = []
        for i in range(len(md.channels)):
            carried = adstock_pt(spend[:, i], decay[i], md.adstock_length)
            saturated = hill_pt(carried, half_sat[i], slope[i])
            media_terms.append(effect[i] * saturated)
        media = pt.sum(pt.stack(media_terms), axis=0)

        mu = (
            intercept
            + trend * trend_feature
            + pt.dot(sin_feat, seas_sin)
            + pt.dot(cos_feat, seas_cos)
            + control * md.control
            + media
        )
        pm.Normal("revenue", mu=mu, sigma=noise, observed=md.revenue_scaled, dims="week")
    return model


def fit(model: pm.Model, sampling: dict) -> tuple[az.InferenceData, dict]:
    """Sample with NUTS. Returns the trace and a record of what actually ran.

    The record notes the sampler used, wall time, and whether the draw budget was
    halved because a fit exceeded ``max_minutes``.
    """
    draws = int(sampling["draws"])
    tune = int(sampling["tune"])
    info = {
        "sampler": None,
        "chains": int(sampling["chains"]),
        "tune": tune,
        "draws": draws,
        "target_accept": float(sampling["target_accept"]),
        "seed": int(sampling["seed"]),
        "elapsed_seconds": None,
        "deviations": [],
    }
    cap = float(sampling.get("max_minutes", 0) or 0) * 60.0
    for attempt in range(3):
        start = time.time()
        idata, sampler = _sample(model, sampling, tune, draws)
        elapsed = time.time() - start
        info.update(sampler=sampler, tune=tune, draws=draws, elapsed_seconds=round(elapsed, 1))
        if cap and elapsed > cap and attempt < 2:
            info["deviations"].append(
                f"fit took {elapsed / 60:.1f} minutes, above the cap of {cap / 60:.0f}; "
                f"draws and tuning halved from {draws}/{tune}"
            )
            draws, tune = max(draws // 2, 100), max(tune // 2, 100)
            continue
        break
    return idata, info


def _sample(model: pm.Model, sampling: dict, tune: int, draws: int):
    kwargs = dict(
        draws=draws,
        tune=tune,
        chains=int(sampling["chains"]),
        cores=int(sampling["chains"]),
        target_accept=float(sampling["target_accept"]),
        random_seed=int(sampling["seed"]),
        progressbar=False,
    )
    wanted = str(sampling.get("sampler", "pymc"))
    with model:
        if wanted == "nutpie":
            try:
                import nutpie  # noqa: F401

                return pm.sample(nuts_sampler="nutpie", **kwargs), "nutpie"
            except ImportError:
                pass
        return pm.sample(**kwargs), "pymc"


def fit_with_ladder(md: ModelData, config: dict) -> tuple[object, dict, dict]:
    """Fit, and when a diagnostic gate fails, adjust the sampler in a fixed, recorded order.

    Divergences (or a high R-hat) raise target_accept one rung (0.95, then 0.99).
    Too few effective draws double the draw count at the same rung, at most twice.
    The sequence stops at the first fit that passes every gate; if none does, the
    attempt with the fewest divergences and then the highest effective sample size
    is kept. Every attempt is written to the diagnostics record, so a failed gate is
    never silent.
    """
    base = dict(config["sampling"])
    rungs = [float(base["target_accept"]), 0.95, 0.99]
    rung = 0
    draws = int(base["draws"])
    attempts: list[dict] = []
    best = None
    tried: set[tuple[float, int]] = set()
    while (rungs[rung], draws) not in tried and len(attempts) < 6:
        sampling = dict(base, target_accept=rungs[rung], draws=draws)
        tried.add((rungs[rung], draws))
        built = build_model(md, config["priors"])
        idata, info = fit(built, sampling)
        diag = diagnostics.summarise(idata, config["diagnostics"], extra={"fit": info})
        attempts.append(
            {
                "target_accept": rungs[rung],
                "draws": draws,
                "divergences": diag["divergences"],
                "max_rhat": diag["max_rhat"],
                "min_ess": min(diag["min_ess_bulk"], diag["min_ess_tail"]),
                "pass_all": diag["pass_all"],
                "elapsed_seconds": info["elapsed_seconds"],
            }
        )
        key = (diag["pass_all"], diag["pass_divergences"], -diag["divergences"],
               min(diag["min_ess_bulk"], diag["min_ess_tail"]))
        if best is None or key > best[0]:
            best = (key, idata, info, diag)
        if diag["pass_all"]:
            break
        if not diag["pass_divergences"] or not diag["pass_rhat"]:
            if rung + 1 < len(rungs):
                rung += 1
                continue
            break
        if draws < 4 * int(base["draws"]):
            draws *= 2
            continue
        break
    _, idata, info, diag = best
    diag["attempts"] = attempts
    if len(attempts) > 1:
        diag["deviations"] = [
            "sampler settings changed after a failed gate: " + "; ".join(
                f"target_accept {a['target_accept']}, draws {a['draws']} gave "
                f"{a['divergences']} divergences and min ESS {a['min_ess']:.0f}"
                for a in attempts
            )
        ]
    return idata, info, diag


# ---------------------------------------------------------------------------
# Posterior handling in numpy
# ---------------------------------------------------------------------------


@dataclass
class Posterior:
    """Posterior draws stacked over chains, as numpy arrays keyed by parameter name."""

    draws: dict[str, np.ndarray]
    channels: list[str]

    @property
    def n(self) -> int:
        return int(self.draws["intercept"].shape[0])

    def subset(self, n: int, seed: int = 0) -> Posterior:
        """A deterministic random subset of ``n`` draws."""
        rng = np.random.default_rng(seed)
        idx = np.sort(rng.choice(self.n, size=min(n, self.n), replace=False))
        return Posterior({k: v[idx] for k, v in self.draws.items()}, self.channels)


def extract(idata: az.InferenceData) -> Posterior:
    post = idata.posterior.stack(sample=("chain", "draw"))
    draws = {}
    for name in PARAM_NAMES:
        arr = post[name].transpose("sample", ...).to_numpy()
        draws[name] = np.asarray(arr, dtype=float)
    return Posterior(draws, [str(c) for c in idata.posterior["channel"].to_numpy()])


def summary_table(idata: az.InferenceData) -> pd.DataFrame:
    """ArviZ summary with 90 percent HDI, for the posterior summary CSV."""
    table = az.summary(idata, hdi_prob=0.90)
    table.index.name = "parameter"
    return table.reset_index()


def media_contributions(post: Posterior, md: ModelData) -> np.ndarray:
    """Weekly contribution per draw and channel, money units, shape (S, T, C)."""
    x = md.spend_scaled
    out = np.zeros((post.n, md.n_weeks, len(md.channels)))
    for c in range(len(md.channels)):
        for s in range(post.n):
            carried = adstock(x[:, c], post.draws["decay"][s, c], md.adstock_length)
            out[s, :, c] = post.draws["effect"][s, c] * hill(
                carried, post.draws["half_saturation"][s, c], post.draws["slope"][s, c]
            )
    return out * md.revenue_mean


def baseline_mean(post: Posterior, md: ModelData) -> np.ndarray:
    """Intercept, trend, seasonality and control per draw, money units, shape (S, T)."""
    sin_feat, cos_feat = md.fourier_features()
    d = post.draws
    out = (
        d["intercept"][:, None]
        + d["trend"][:, None] * md.trend_feature[None, :]
        + d["seasonality_sin"] @ sin_feat.T
        + d["seasonality_cos"] @ cos_feat.T
        + d["control"][:, None] * md.control[None, :]
    )
    return out * md.revenue_mean


def predict(post: Posterior, md: ModelData, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Expected revenue and posterior predictive draws, money units, shape (S, T) each."""
    mu = baseline_mean(post, md) + media_contributions(post, md).sum(axis=2)
    rng = np.random.default_rng(seed)
    sigma = post.draws["noise"][:, None] * md.revenue_mean
    return mu, mu + rng.normal(size=mu.shape) * sigma


def write_posterior(post: Posterior, md: ModelData, out: Path) -> None:
    """Draw-level parameters and the scaling constants, for Layer D."""
    cols = {}
    for name in ("intercept", "trend", "control", "noise"):
        cols[name] = post.draws[name]
    for i, ch in enumerate(md.channels):
        for name in ("decay", "half_saturation", "slope", "effect"):
            cols[f"{name}__{ch}"] = post.draws[name][:, i]
    pd.DataFrame(cols).to_csv(out / "posterior_draws.csv", index=False, lineterminator="\n")
    meta = {
        "channels": md.channels,
        "spend_means": {ch: float(m) for ch, m in zip(md.channels, md.spend_means, strict=True)},
        "spend_mean_week": {ch: float(md.spend[:, i].mean()) for i, ch in enumerate(md.channels)},
        "spend_max_week": {ch: float(md.spend[:, i].max()) for i, ch in enumerate(md.channels)},
        "revenue_mean": md.revenue_mean,
        "weeks": md.n_weeks,
        "adstock_length": md.adstock_length,
    }
    with open(out / "model_data.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, sort_keys=True)
        fh.write("\n")
