"""The fourth architectural guard (D-23): SPEC-08 section 2 layout, with no
allowlist, plus the contract-first cross-check against `docs/MODULE_CONTRACTS.md`.

The two frozen sets below are deliberately NOT an allowlist of exceptions — they
*are* the canonical layout itself (SPEC-08 section 2, plus the four D-14 additions:
`.github/`, `.planning/`, `uv.lock`, `.gitattributes`). A new top-level entry or
`src/ambo/` subpackage belongs in SPEC-08 section 2 via an ADR before it belongs in
either set here.

Both checks enumerate with `git ls-files`, so untracked scratch files and
gitignored-by-design artifacts are out of scope by construction — only what is
actually tracked can trip these guards.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

# SPEC-08 section 2's canonical top-level tree + D-14's four additions.
PERMITTED_TOP_LEVEL: frozenset[str] = frozenset(
    {
        "PROJECT_CHARTER.md",
        "AGENTS.md",
        "README.md",
        "LIMITATIONS.md",  # Phase 9 deliverable — absence must not fail this test.
        "LICENSE",
        "Makefile",
        "pyproject.toml",
        ".pre-commit-config.yaml",  # arrives in plan 01-08 — absence must not fail this test.
        ".gitignore",
        ".env.example",
        "config",
        "src",
        "dbt",
        "scripts",
        "data",
        "exports",
        "reports",
        "dashboards",
        "docs",
        "tests",
        # D-14 additions:
        ".github",
        ".planning",
        "uv.lock",
        ".gitattributes",
    }
)

# SPEC-08 section 2's `src/ambo/` package list.
PERMITTED_SRC_AMBO_SUBPACKAGES: frozenset[str] = frozenset(
    {
        "simulate",
        "intake",
        "model",
        "validate",
        "decide",
        "report",
        "common",
    }
)

# `docs/MODULE_CONTRACTS.md` level-3 headings are exactly the module's
# repository-relative path, e.g. "### src/ambo/common/config.py".
_MODULE_HEADING_RE = re.compile(r"^### (src/ambo/\S+\.py)\s*$", re.MULTILINE)


def _tracked_files(repo_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def test_top_level_entries_are_all_in_the_canonical_layout(repo_root: Path) -> None:
    tracked = _tracked_files(repo_root)
    assert tracked, "git ls-files returned nothing — the scan itself is broken."

    top_level = {line.split("/", 1)[0] for line in tracked}
    unexpected = top_level - PERMITTED_TOP_LEVEL

    assert not unexpected, (
        f"Top-level entr(y/ies) not in the SPEC-08 section 2 (+ D-14) canonical "
        f"layout: {sorted(unexpected)}. This is deliberately not an allowlist of "
        f"exceptions — a new top-level entry needs an ADR amending SPEC-08 section 2 "
        f"before it belongs here. Scanned {len(top_level)} top-level entries across "
        f"{len(tracked)} tracked files."
    )


def test_src_ambo_subpackages_are_all_permitted(repo_root: Path) -> None:
    tracked = _tracked_files(repo_root)
    subpackages = {
        parts[2]
        for line in tracked
        if len(parts := line.split("/")) > 3 and parts[0] == "src" and parts[1] == "ambo"
    }
    assert subpackages, "No src/ambo/ subpackages discovered — the scan is broken."

    unexpected = subpackages - PERMITTED_SRC_AMBO_SUBPACKAGES
    assert not unexpected, (
        f"Unexpected src/ambo/ subpackage(s): {sorted(unexpected)}. A new subpackage "
        f"needs an ADR amending SPEC-08 section 2. Scanned {len(subpackages)} "
        f"subpackage(s)."
    )


def _module_contract_entries(repo_root: Path) -> list[str]:
    contracts_path = repo_root / "docs" / "MODULE_CONTRACTS.md"
    text = contracts_path.read_text(encoding="utf-8")
    return _MODULE_HEADING_RE.findall(text)


def _src_ambo_modules(repo_root: Path) -> set[str]:
    modules: set[str] = set()
    for path in (repo_root / "src" / "ambo").rglob("*.py"):
        if path.name == "__init__.py":
            continue
        modules.add(path.relative_to(repo_root).as_posix())
    return modules


def test_module_contracts_match_src_ambo_modules_exactly(repo_root: Path) -> None:
    """Contract-first, both directions (D-23): a module with no entry fails, and an
    entry for a module that no longer exists fails equally. A duplicate heading is
    caught separately so its failure message says "duplicate", not "mismatch"."""
    entries = _module_contract_entries(repo_root)
    entries_set = set(entries)

    assert len(entries) == len(entries_set), (
        "docs/MODULE_CONTRACTS.md has a duplicate module heading for: "
        f"{sorted({e for e in entries_set if entries.count(e) > 1})}"
    )

    modules = _src_ambo_modules(repo_root)

    missing_entries = modules - entries_set
    orphan_entries = entries_set - modules

    assert not missing_entries, (
        f"Module(s) under src/ambo/ with no docs/MODULE_CONTRACTS.md entry: "
        f"{sorted(missing_entries)}. The contract is written in the same PR as the "
        f"module it describes (D-23), never back-filled afterward."
    )
    assert not orphan_entries, (
        f"docs/MODULE_CONTRACTS.md entry(ies) naming module(s) that do not exist: "
        f"{sorted(orphan_entries)}"
    )

    # D-17 shape: report what was scanned, so a vacuous pass (few or zero modules in
    # a given subpackage) is visibly vacuous rather than silently skipped.
    print(
        f"module-contract cross-check: {len(modules)} src/ambo/ module(s), "
        f"{len(entries_set)} docs/MODULE_CONTRACTS.md entr(y/ies) — sets equal."
    )
