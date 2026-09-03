"""Tests for `ambo.model.priors` (T-303, MD-040).

Implements: MD-040
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from ambo.common.config import SPEC_CHANNEL_ORDER, repo_root
from ambo.common.errors import FitError
from ambo.model.priors import SYNTHETIC_PRIORS_RELATIVE, ChannelPrior, load_priors


def _synthetic_path() -> Path:
    return repo_root() / SYNTHETIC_PRIORS_RELATIVE


def test_synthetic_priors_load() -> None:
    priors = load_priors(_synthetic_path())
    assert tuple(priors.channels) == SPEC_CHANNEL_ORDER
    assert len(priors.channels) == 7


def test_md040_channel_entries_are_value_equal() -> None:
    """Layer P priors contain no channel-differentiated numbers (MD-040)."""
    priors = load_priors(_synthetic_path())
    reference: ChannelPrior = next(iter(priors.channels.values()))
    for name, channel in priors.channels.items():
        assert channel == reference, name
    assert reference.lam.a == 2.0
    assert reference.lam.b == 4.0
    assert reference.K.shape == 2.0
    assert reference.K.rate == 1.3
    assert reference.s.shape == 3.0
    assert reference.s.rate == 2.0
    assert reference.s.lower == 0.3
    assert reference.s.upper == 3.0
    assert reference.beta.sigma == 0.15


def test_globals_match_spec_04_section_4() -> None:
    g = load_priors(_synthetic_path()).globals
    assert (g.alpha.mu, g.alpha.sigma) == (1.0, 0.3)
    assert (g.tau.mu, g.tau.sigma) == (0.0, 0.1)
    assert (g.gamma.mu, g.gamma.sigma) == (0.0, 0.15)
    assert (g.delta_promo.mu, g.delta_promo.sigma) == (0.1, 0.05)
    assert (g.delta_advent.mu, g.delta_advent.sigma) == (0.3, 0.15)
    assert (g.delta_jan.mu, g.delta_jan.sigma) == (-0.1, 0.1)
    assert g.sigma.sigma == 0.1


def test_priors_real_yaml_does_not_exist() -> None:
    assert not (repo_root() / "config" / "priors_real.yaml").is_file()


def test_extra_channel_field_is_forbidden(tmp_path: Path) -> None:
    raw: dict[str, Any] = yaml.safe_load(_synthetic_path().read_text(encoding="utf-8"))
    raw["channels"]["meta"]["surprise"] = 1
    path = tmp_path / "priors.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(FitError, match="surprise"):
        load_priors(path)


def test_extra_top_level_key_is_forbidden(tmp_path: Path) -> None:
    raw: dict[str, Any] = yaml.safe_load(_synthetic_path().read_text(encoding="utf-8"))
    raw["unexpected"] = True
    path = tmp_path / "priors.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(FitError, match="unexpected"):
        load_priors(path)


def test_missing_file_raises_fit_error(tmp_path: Path) -> None:
    missing = tmp_path / "absent.yaml"
    with pytest.raises(FitError, match="not found"):
        load_priors(missing)
