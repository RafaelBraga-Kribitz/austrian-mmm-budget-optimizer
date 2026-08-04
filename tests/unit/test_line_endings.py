"""D-22 proof: no tracked text file contains a carriage-return byte.

Enumerates tracked files with `git ls-files`, then filters to those git itself
considers text by consulting `git check-attr text` -- never a hardcoded extension
list, so this test tracks `.gitattributes` rather than duplicating it. A path git
reports as `unset` (the `binary` macro, e.g. `*.parquet`) is skipped; `set` and
`auto` (the `.gitattributes` catch-all `* text=auto eol=lf`) both count as text.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _tracked_files(repo_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def _text_verdicts(repo_root: Path, paths: list[str]) -> dict[str, str]:
    """One `git check-attr text` call over every tracked path. Output is one line
    per path: `<path>: text: <set|unset|auto|unspecified>`."""
    if not paths:
        return {}
    result = subprocess.run(
        ["git", "check-attr", "text", "--", *paths],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    verdicts: dict[str, str] = {}
    for line in result.stdout.splitlines():
        path_part, _, rest = line.rpartition(": text: ")
        if path_part:
            verdicts[path_part] = rest.strip()
    return verdicts


def test_no_tracked_text_file_contains_a_carriage_return(repo_root: Path) -> None:
    tracked = _tracked_files(repo_root)
    assert tracked, "git ls-files returned nothing -- the scan itself is broken."

    verdicts = _text_verdicts(repo_root, tracked)
    text_files = [p for p in tracked if verdicts.get(p) != "unset"]
    assert text_files, "No file git treats as text was found -- the scan is broken."

    offenders: list[str] = []
    for rel in text_files:
        data = (repo_root / rel).read_bytes()
        if b"\r" in data:
            offenders.append(rel)

    assert not offenders, f"Tracked text file(s) contain a carriage-return byte: {offenders}"
    print(
        f"line-endings guard: scanned {len(text_files)} text file(s) of "
        f"{len(tracked)} tracked file(s), 0 carriage returns."
    )
