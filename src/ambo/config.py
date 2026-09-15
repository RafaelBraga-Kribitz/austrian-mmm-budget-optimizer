"""Shared constants for the five-channel Layer P build (STATUS D-05).

Implements: SIM-002, MD-020, MD-050. Channel taxonomy deviation: ADR-012.
"""

from __future__ import annotations

from pathlib import Path

CHANNEL_IDS: tuple[str, ...] = (
    "tv",
    "radio",
    "print",
    "paid_search",
    "paid_social",
)

CHANNEL_LABELS: dict[str, str] = {
    "tv": "TV",
    "radio": "Radio",
    "print": "Print",
    "paid_search": "Paid Search",
    "paid_social": "Paid Social",
}

# Offline channels have no platform dashboard (SPEC-01 §6 analogue).
OFFLINE_CHANNELS: frozenset[str] = frozenset({"tv", "radio", "print"})
ONLINE_CHANNELS: frozenset[str] = frozenset({"paid_search", "paid_social"})

N_WEEKS = 156
START_ISO_YEAR = 2022
START_ISO_WEEK = 1
SEED = 101
HOLDOUT_START_WEEK = 131  # 1-indexed; weeks 131–156 are the holdout (STATUS §13)

ADSTOCK_LENGTH = 8  # MD-020
ADSTOCK_NORMALIZE = True  # MD-020: w_i = λ^i / Σ λ^i; ss adstock = spend
FOURIER_PERIOD_WEEKS = 52.18
FOURIER_ORDER = 4

B0 = 60_000.0
GROWTH = 0.001
PROMO_MULTIPLIER = 1.15
AOV_BASE = 95.0
AOV_ADVENT_BONUS = 10.0
NOISE_SHARE = 0.04  # σ = this × mean(base)

# Weakly informative, channel-agnostic Layer P priors (MD-040).
LAM_A, LAM_B = 2.0, 4.0
K_SHAPE, K_RATE = 2.0, 1.3
S_SHAPE, S_RATE = 4.0, 3.0  # MD-073 rung 3 (unused once rung 4 fixes s=1)
S_LOWER, S_UPPER = 0.5, 2.5
S_FIXED = 1.0  # MD-073 rung 4: logistic saturation; changes the model class
BETA_SIGMA = 0.15
ALPHA_MU, ALPHA_SIGMA = 1.0, 0.3
TAU_SIGMA = 0.1
GAMMA_SIGMA = 0.15
DELTA_HOLIDAY_MU, DELTA_HOLIDAY_SIGMA = 0.10, 0.10
DELTA_PROMO_MU, DELTA_PROMO_SIGMA = 0.10, 0.05
DELTA_ADVENT_MU, DELTA_ADVENT_SIGMA = 0.30, 0.15
DELTA_JAN_MU, DELTA_JAN_SIGMA = -0.10, 0.10
SIGMA_SIGMA = 0.10

SAMPLER_DRAWS = 1000
SAMPLER_TUNE = 1000
SAMPLER_CHAINS = 4
SAMPLER_SEED = 42
TARGET_ACCEPT = 0.95  # MD-073 rung 1: 0.9 left 53 divergences on Layer P
NUTPIE_FALLBACK = "pymc"

RESPONSE_GRID_POINTS = 21
RESPONSE_GRID_MAX_MULT = 1.5  # MD-082
EXTRAPOLATION_MULT = 1.3  # DC-203(b)
OPTIMIZER_DRAWS = 500  # DC-202
OPTIMIZER_RESTARTS = 20
HDI_PROB = 0.90

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "synthetic"
REPORTS_DIR = REPO_ROOT / "reports"
POSTERIOR_NC = DATA_DIR / "posterior.nc"


def repo_root() -> Path:
    return REPO_ROOT
