"""The leak scanner: pattern subset, full mode, staged mode (AG-045, GB section 8).

Implements: REQ-scope-out, REQ-dl8-quality

Owning SPEC: SPEC-08 section 1 (EB-002) and section 4 (EB-041); the M0 scope decision
is D-26 (`.planning/phases/01-repository-foundation/01-CONTEXT.md`), tracked as R-11
on `docs/RISK_REGISTER.md`. This is one of the four governance showpieces (GB section
8): a script a reviewer runs, not a promise.

IN SCOPE — three pattern classes, stated here so the gate's precision is a documented
decision, not an omission:

1. `PRIVATE_DROP_PATTERNS` — the resolved `AMBO_PRIVATE_DROP` value, in whatever form
   it appears. Two checks make up this class: (a) the literal resolved path from
   `load_settings().private_drop`, matched case-insensitively with both separator
   styles normalized (resolved fresh at scan time, since the value is only known at
   scan time — see `_resolve_private_drop_needles`); (b) a generic shape for a
   Windows or POSIX absolute path immediately adjacent to the `AMBO_PRIVATE_DROP`
   name itself (the constant below), which catches a path pasted into a committed
   file even on a machine where the variable is unset. Scans every tracked text
   file, whole tree — except `.env.example`, the one sanctioned location for a
   fictional `AMBO_PRIVATE_DROP=<path>` line (01-02-PLAN.md); the *literal* check
   still covers that file, only the generic *shape* check exempts it.
2. `CONTACT_PATTERNS` — email, URL and Austrian phone shapes. Scoped to
   `CONTACT_SCAN_ROOTS` (`data/real_anon/`, `reports/ingestion/`) only.
3. `CURRENCY_LITERAL_PATTERN` — a currency-formatted literal. Scoped to notebook
   files (`*.ipynb`) only, where output cells can carry values that never belonged
   in the repository and where `nbstripout` already runs.

OUT OF SCOPE, by decision, not omission:

- anonymized euro figures under `exports/` — committed by design (EB-081, DL-1)
- euro figures anywhere in `docs/`
- any general secret-shaped string outside the three scoped classes above

Widening this set is Phase 6 work (R-11 on the risk register, revisited explicitly by
T-501..T-506 before real data lands) — not an ad-hoc loosening today.

Three modes: the pattern subset above (default, CI-safe), `--full` (subset plus the
`AMBO_PRIVATE_DROP/blocklist.txt` values, skipped gracefully when the drop or the
file is absent), and `--staged` (`git diff --cached -U0` only, for the pre-commit
hook — fast regardless of repository size).

Exit codes: 0 clean, 1 findings, 2 usage error.

A finding never carries the matched text. `Finding` has no field that could hold it —
a finding identifies a location, a pattern class and a hash prefix; a reviewer who
needs the value opens the file locally. This is the structure, not a formatting
convention, and it is why nothing in this module ever interpolates a match into a
message, an exception or a log record.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from collections.abc import Callable, Iterable, Iterator, Sequence
from pathlib import Path
from typing import NamedTuple, NoReturn

from ambo.common.config import load_settings, repo_root

# ---------------------------------------------------------------------------
# Pattern classes (compiled once at import, per the < 10 s whole-tree budget).
# ---------------------------------------------------------------------------

# The one file where a fictional `AMBO_PRIVATE_DROP=<path>` line is expected by
# design (01-02-PLAN.md) — excluded from the generic-shape check only.
_ENV_EXAMPLE_PATH = ".env.example"

_PRIVATE_DROP_ENV_VAR = "AMBO_PRIVATE_DROP"

# Generic private-drop-adjacent path shape: an absolute Windows path (`C:\...` or
# `C:/...`) or an absolute POSIX path (`/...`) immediately assigned to the env
# var's own name via `=` or `:`, e.g. `AMBO_PRIVATE_DROP=<abs-path>` (Windows form)
# or `AMBO_PRIVATE_DROP: <abs-path>` (POSIX form). Catches a path pasted into a
# committed file even where the variable itself is unset on the scanning machine.
# The two examples above are deliberately written with a `<abs-path>` placeholder
# rather than a literal path -- the pattern's own path character class excludes
# `<`/`>`, so a literal example here would self-match this file when the scanner
# runs over its own source (this repository's `leak` CI job does exactly that;
# see 01-09's fix-forward). Requiring an
# assignment operator (rather than bare adjacency) is deliberate: prose that merely
# *mentions* the variable name (e.g. "the `AMBO_PRIVATE_DROP` env var") does not
# match, and neither does the project's own shell-interpolation documentation style
# (`$AMBO_PRIVATE_DROP/staged/`, a relative continuation, not an assigned value).
PRIVATE_DROP_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        rf"{_PRIVATE_DROP_ENV_VAR}\s{{0,1}}[:=]\s{{0,1}}(?:[A-Za-z]:[\\/][^\s\"'<>]+|/[^\s\"'<>]+)",
        re.IGNORECASE,
    ),
)

# Path prefixes CONTACT_PATTERNS applies to; everything else is out of scope.
CONTACT_SCAN_ROOTS: tuple[str, ...] = ("data/real_anon/", "reports/ingestion/")

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_URL_RE = re.compile(r"\bhttps?://[^\s\"'<>]+", re.IGNORECASE)
# Requires an Austrian international (+43 / 0043) or national (leading 0) prefix
# followed by at least two more digit groups — not any long digit run, since a
# spend figure is a long digit sequence too.
_AT_PHONE_RE = re.compile(r"(?<!\d)(?:\+43|0043|0)(?:[\s./-]?\d{2,4}){2,4}(?!\d)")

CONTACT_PATTERNS: tuple[re.Pattern[str], ...] = (_EMAIL_RE, _URL_RE, _AT_PHONE_RE)

# A currency-formatted literal, either `€ 1.234,56` / `1.234,56 €` (Austrian
# thousands-dot/decimal-comma) or `€1,234.56` / `1,234.56€` (thousands-comma/
# decimal-dot) forms.
CURRENCY_LITERAL_PATTERN: re.Pattern[str] = re.compile(
    r"(?:€\s?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?|\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s?€)"
)


def _not_env_example(rel_posix: str) -> bool:
    """Scope predicate for the private-drop generic-shape class: every file except
    `.env.example` (see module docstring)."""
    return rel_posix != _ENV_EXAMPLE_PATH


def _under_contact_scan_roots(rel_posix: str) -> bool:
    return any(rel_posix.startswith(root) for root in CONTACT_SCAN_ROOTS)


def _is_notebook(rel_posix: str) -> bool:
    return rel_posix.endswith(".ipynb")


# (pattern class name, compiled patterns, scope predicate over a repo-relative
# posix-style path). Order matches the module docstring's IN SCOPE list.
_STATIC_PATTERN_CLASSES: tuple[
    tuple[str, tuple[re.Pattern[str], ...], Callable[[str], bool]], ...
] = (
    ("private_drop", PRIVATE_DROP_PATTERNS, _not_env_example),
    ("contact", CONTACT_PATTERNS, _under_contact_scan_roots),
    ("currency_literal", (CURRENCY_LITERAL_PATTERN,), _is_notebook),
)

_HASH_PREFIX_LENGTH = 8
_BINARY_PROBE_BYTES = 8000


class Finding(NamedTuple):
    """One leak-scan hit. Immutable, and structurally incapable of carrying the
    matched text: there is no field for it, so no code path here can print a match
    by accident (the redaction contract's structural half — see module docstring).
    """

    path: str
    line: int
    pattern_class: str
    match_hash: str


def _hash_prefix(matched_text: str) -> str:
    """A short hex digest identifying a match without revealing it."""
    return hashlib.sha256(matched_text.encode("utf-8")).hexdigest()[:_HASH_PREFIX_LENGTH]


def _iter_matches_for_line(line: str, patterns: Iterable[re.Pattern[str]]) -> Iterator[str]:
    for pattern in patterns:
        for match in pattern.finditer(line):
            yield match.group(0)


def _find_needle_case_insensitive(line: str, needle: str) -> str | None:
    """Return the matching substring of `line` (original case) if `needle` occurs
    in it case-insensitively, else `None`."""
    if not needle:
        return None
    idx = line.lower().find(needle.lower())
    if idx == -1:
        return None
    return line[idx : idx + len(needle)]


def _scan_single_line(
    rel_posix: str,
    line_no: int,
    line: str,
    needles: Sequence[str] = (),
    blocklist: Sequence[str] | None = None,
) -> list[Finding]:
    """Apply every pattern class to one line of one file and return its findings."""
    findings: list[Finding] = []

    for class_name, patterns, scope in _STATIC_PATTERN_CLASSES:
        if not scope(rel_posix):
            continue
        for matched_text in _iter_matches_for_line(line, patterns):
            findings.append(Finding(rel_posix, line_no, class_name, _hash_prefix(matched_text)))

    for needle in needles:
        matched_text = _find_needle_case_insensitive(line, needle)
        if matched_text is not None:
            findings.append(Finding(rel_posix, line_no, "private_drop", _hash_prefix(matched_text)))

    if blocklist:
        for needle in blocklist:
            matched_text = _find_needle_case_insensitive(line, needle)
            if matched_text is not None:
                findings.append(
                    Finding(rel_posix, line_no, "blocklist", _hash_prefix(matched_text))
                )

    return findings


def _resolve_private_drop_needles() -> list[str]:
    """Return the current `AMBO_PRIVATE_DROP` value in every separator form it
    might appear in a committed file, or `[]` when the variable is unset.

    Resolved fresh through `load_settings().private_drop` on every call — the
    single resolution path EB-041 requires (the same one the pre-commit hook, CI
    and `PrivatePathFilter` all use) — rather than cached at import, so a test that
    sets the environment variable and clears `load_settings`'s cache genuinely
    changes what this scanner looks for.
    """
    private_drop = load_settings().private_drop
    if private_drop is None:
        return []
    raw = str(private_drop)
    return [raw, raw.replace("\\", "/"), raw.replace("/", "\\")]


def _git_ls_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=root, check=True, capture_output=True, text=True
    )
    return [line for line in result.stdout.splitlines() if line]


def _read_text_if_not_binary(path: Path) -> str | None:
    """Read `path` once as bytes, skip it if git-style binary (a NUL byte in the
    first probe window), otherwise decode as UTF-8. Returns `None` for anything
    that cannot be scanned as text, so callers never spend time decoding a file the
    binary check already excluded."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in raw[:_BINARY_PROBE_BYTES]:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def scan_tree(root: Path, blocklist: Sequence[str] | None = None) -> list[Finding]:
    """Scan every tracked file under `root` and return all findings.

    Enumerates via `git ls-files` (tracked files only — untracked scratch and
    gitignored artifacts are out of scope by construction), skips binary files,
    and applies every in-scope pattern class to each remaining file's lines. When
    `blocklist` is supplied, each of its values is matched as an additional
    pattern class across the whole tree (full mode).
    """
    needles = _resolve_private_drop_needles()
    findings: list[Finding] = []

    for rel in _git_ls_files(root):
        abs_path = root / rel
        if not abs_path.is_file():
            continue
        text = _read_text_if_not_binary(abs_path)
        if text is None:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            findings.extend(_scan_single_line(rel, line_no, line, needles, blocklist))

    return findings


_HUNK_HEADER_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _parse_staged_added_lines(diff_text: str) -> Iterator[tuple[str, int, str]]:
    """Yield `(path, new_file_line_number, line_text)` for every added line in a
    `git diff --cached -U0` unified diff. Removed and context lines never advance
    the new-file line counter; only `+` lines do."""
    current_path: str | None = None
    next_line = 0

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("+++ "):
            target = raw_line[len("+++ ") :]
            current_path = None if target == "/dev/null" else target.split("/", 1)[-1]
            continue
        if raw_line.startswith("@@"):
            match = _HUNK_HEADER_RE.match(raw_line)
            if match:
                next_line = int(match.group(1))
            continue
        if raw_line.startswith("+"):
            if current_path is not None:
                yield current_path, next_line, raw_line[1:]
            next_line += 1


def scan_staged() -> list[Finding]:
    """Scan only `git diff --cached -U0` (added lines only) and return all
    findings. Reads the repository root via `ambo.common.config.repo_root()`, the
    same resolution every other module uses. Fast regardless of repository size,
    which is what makes it safe to run on every commit."""
    root = repo_root()
    diff = subprocess.run(
        ["git", "diff", "--cached", "-U0", "--no-color"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    needles = _resolve_private_drop_needles()
    findings: list[Finding] = []
    for rel, line_no, line in _parse_staged_added_lines(diff):
        findings.extend(_scan_single_line(rel, line_no, line, needles))
    return findings


def _load_blocklist(private_drop: Path) -> list[str] | None:
    """Read one distinctive value per line from `<private_drop>/blocklist.txt`.

    Returns `None` when the file is absent — the "blocklist unavailable" state the
    caller reports as a graceful skip — and a (possibly empty) list of stripped,
    non-blank lines when it is present. `None` and `[]` are deliberately distinct:
    the first means "nothing to check against", the second means "the file exists
    but declares no values".
    """
    blocklist_path = private_drop / "blocklist.txt"
    if not blocklist_path.is_file():
        return None
    return [
        stripped
        for raw_line in blocklist_path.read_text(encoding="utf-8").splitlines()
        if (stripped := raw_line.strip())
    ]


class _UsageError(Exception):
    """Raised by `_ArgParser.error` instead of calling `sys.exit` directly, so
    `main()` stays a plain argv -> exit-code function with a single process-exit
    call site (the module's own `__main__` guard)."""


class _ArgParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # type: ignore[override]
        raise _UsageError(message)


def _build_arg_parser() -> _ArgParser:
    parser = _ArgParser(
        prog="leak_scan.py",
        description=(
            "AG-045 leak scanner (D-26 M0 pattern subset). Three modes: the default "
            "pattern subset, --full (subset plus the AMBO_PRIVATE_DROP blocklist), "
            "and --staged (git diff --cached -U0 only, for the pre-commit hook)."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--full",
        action="store_true",
        help="Also scan the AMBO_PRIVATE_DROP blocklist, when available.",
    )
    mode.add_argument(
        "--staged",
        action="store_true",
        help="Scan only the cached diff (git diff --cached -U0) -- fast pre-commit mode.",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Override the scanned root for whole-tree modes (default: the repository root).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse `argv`, run the requested scan mode, print findings one per line as
    `path:line pattern-class hash-prefix`, and return the process exit code: 0
    clean, 1 findings, 2 usage error. Never calls `sys.exit` itself.
    """
    parser = _build_arg_parser()
    try:
        args = parser.parse_args(argv)
    except _UsageError as exc:
        print(parser.format_usage(), end="", file=sys.stderr)
        print(f"leak_scan.py: error: {exc}", file=sys.stderr)
        return 2

    if args.staged:
        findings = scan_staged()
    else:
        root = Path(args.root).resolve() if args.root else repo_root()
        blocklist: list[str] | None = None
        if args.full:
            private_drop = load_settings().private_drop
            if private_drop is None:
                print(
                    "leak_scan: --full requested but AMBO_PRIVATE_DROP is unset -- "
                    "blocklist unavailable, running the pattern subset only.",
                    file=sys.stderr,
                )
            else:
                blocklist = _load_blocklist(private_drop)
                if blocklist is None:
                    print(
                        "leak_scan: --full requested but no blocklist.txt found "
                        "under the private drop -- blocklist unavailable, running "
                        "the pattern subset only.",
                        file=sys.stderr,
                    )
        findings = scan_tree(root, blocklist=blocklist)

    for finding in findings:
        print(f"{finding.path}:{finding.line} {finding.pattern_class} {finding.match_hash}")

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
