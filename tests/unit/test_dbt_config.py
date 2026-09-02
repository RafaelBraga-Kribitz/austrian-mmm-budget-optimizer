"""Pin the two dbt/Python cross-language facts a dbt version bump could silently
break (T-201, plan 03-01, BP-G-03).

`dbt/dbt_project.yml`'s `vars.channel_taxonomy` and `dbt/profiles.yml`'s `dev` output
path are each duplicated knowledge -- the taxonomy also lives in
`config/settings.yaml`'s `channels`, and the warehouse path also lives in
`config/settings.yaml`'s `paths.warehouse`. Per this project's own "tested, not
eliminated" precedent for cross-language duplication, both are pinned here rather
than merged into one home.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from ambo.common.config import load_settings


def _load_dbt_project(repo_root: Path) -> dict:
    dbt_project_path = repo_root / "dbt" / "dbt_project.yml"
    with dbt_project_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _load_dbt_profiles(repo_root: Path) -> dict:
    profiles_path = repo_root / "dbt" / "profiles.yml"
    with profiles_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_dbt_channel_taxonomy_var_equals_settings_channels(repo_root: Path) -> None:
    dbt_project = _load_dbt_project(repo_root)

    dbt_vars = dbt_project.get("vars")
    assert dbt_vars, (
        "dbt/dbt_project.yml has no (or an empty) vars block -- an empty vars block "
        "means this scan is broken, not vacuously passing."
    )

    channel_taxonomy = dbt_vars.get("channel_taxonomy")
    assert channel_taxonomy, (
        "dbt/dbt_project.yml vars.channel_taxonomy is missing or empty -- an empty "
        "list means this scan is broken, not vacuously passing."
    )

    settings_channels = list(load_settings().channels)

    assert channel_taxonomy == settings_channels, (
        "dbt/dbt_project.yml vars.channel_taxonomy must equal config/settings.yaml's "
        f"channels element-for-element and in order (BP-G-03). dbt: {channel_taxonomy!r}, "
        f"settings: {settings_channels!r}."
    )


def test_profiles_dev_path_matches_settings_warehouse(repo_root: Path) -> None:
    profiles = _load_dbt_profiles(repo_root)

    dev_path = profiles["ambo"]["outputs"]["dev"]["path"]

    # The static half of D-23: profiles.yml's committed dev.path string, as written
    # in the YAML, must equal config/settings.yaml's paths.warehouse string, also as
    # written in the YAML -- both are the repository-relative form
    # "data/warehouse/ambo.duckdb". The dynamic half (that the built file actually
    # lands there after a real dbt build) is proven by
    # test_warehouse_build.py::test_warehouse_file_lands_at_settings_path.
    settings_path = repo_root / "config" / "settings.yaml"
    settings_raw = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
    settings_warehouse_raw = settings_raw["paths"]["warehouse"]

    assert dev_path == settings_warehouse_raw, (
        "dbt/profiles.yml ambo.outputs.dev.path must equal config/settings.yaml's "
        f"paths.warehouse string exactly. profiles.yml: {dev_path!r}, "
        f"settings.yaml: {settings_warehouse_raw!r}."
    )
