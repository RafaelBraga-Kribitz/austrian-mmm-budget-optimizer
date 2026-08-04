"""Layer-order and prior-freeze git-ancestry check (GB-501/GB-502, SPEC-09 section 5).

Implements: REQ-dl8-quality

Owning spec: `docs/SPEC-09_governance_quality.md` section 5; the exact git commands
are `docs/EXECUTION_BLUEPRINT/05_IMPLEMENTATION_GUIDES.md` section 10. The M0 scope
decision is D-17 (`.planning/phases/01-repository-foundation/01-CONTEXT.md`): this is
a real, vacuously-correct-today predicate, not a stub. Phase 5 EXTENDS this script in
place -- it does not replace it. There is deliberately no stub marker and no expiry
mechanism: nothing here needs to change when a Layer R artifact first appears, only
the run gains real work to do and reports it.

GB-501: the commit that first adds `reports/recovery/RECOVERY_REPORT.md` (Layer P
proven on disclosed truth) must be a git ancestor of the commit that first adds every
existing Layer R artifact -- the model is proven on truth before it ever touches real
data.

GB-502: the commit of the `prior-freeze-v1` tag must be an ancestor of every Layer R
artifact's first-add commit; `config/priors_real.yaml` must never be touched by any
commit after the freeze commit; and any post-freeze commit touching
`docs/PRIOR_ELICITATION.md` must be a strictly append-only amendment -- every added
line falling under a `## Amendment` heading -- with an ADR landing in the same
post-freeze commit range.

Pre-conditions absent -- no Layer R artifact matches `LAYER_R_GLOBS` and the
`prior-freeze-v1` tag does not exist -- is a real outcome this predicate reports
explicitly, not a skip: exit 0 with a notice naming both facts, so a reader can tell
the check ran and found nothing to verify, not that it was bypassed.

Conventions matched to `scripts/leak_scan.py`: exit 0 clean, 1 violations found, 2
usage error; notices on stdout, errors and violations on stderr.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from ambo.common.config import repo_root

# GB-501: the two Layer R artifact shapes (Guide section 10).
LAYER_R_GLOBS: tuple[str, ...] = ("data/posteriors/R*.parquet", "reports/model/diag_R.md")

RECOVERY_REPORT_PATH = "reports/recovery/RECOVERY_REPORT.md"
PRIORS_REAL_PATH = "config/priors_real.yaml"
PRIOR_ELICITATION_PATH = "docs/PRIOR_ELICITATION.md"
FREEZE_TAG = "prior-freeze-v1"

_AMENDMENT_HEADING_PREFIX = "## Amendment"
_HUNK_HEADER_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)
    return result.stdout


def _git_ls_files(root: Path) -> list[str]:
    return [line for line in _git(root, "ls-files").splitlines() if line]


def first_commit_adding(path: str, root: Path | None = None) -> str | None:
    """Return the hex SHA of the commit that first added `path`.

    The last line of `git log --diff-filter=A --format=%H -- <path>` (`git log`
    prints newest-first, so the last line is the initial add). Returns `None` if
    `path` was never added. `--follow` is deliberately off -- the paths this check
    reasons about are stable by design (module docstring).
    """
    cwd = root if root is not None else repo_root()
    output = _git(cwd, "log", "--diff-filter=A", "--format=%H", "--", path)
    lines = [line for line in output.splitlines() if line]
    return lines[-1] if lines else None


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=root,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _existing_layer_r_artifacts(root: Path) -> list[str]:
    """Every tracked file matching a `LAYER_R_GLOBS` shape, repo-relative posix path."""
    tracked = _git_ls_files(root)
    matches: set[str] = set()
    for pattern in LAYER_R_GLOBS:
        matches.update(fnmatch.filter(tracked, pattern))
    return sorted(matches)


def _tag_exists(root: Path, tag: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _tag_commit(root: Path, tag: str) -> str:
    return _git(root, "rev-list", "-n", "1", tag).strip()


def _commits_touching(root: Path, rev_range: str, path: str) -> list[str]:
    output = _git(root, "log", "--format=%H", rev_range, "--", path)
    return [line for line in output.splitlines() if line]


def _diff_is_append_only(root: Path, commit: str, path: str) -> tuple[bool, list[int]]:
    """Return `(append_only, new_file_hunk_start_lines)` for `commit`'s own change to
    `path` (a single-commit diff against its parent, not a cumulative range diff).
    `append_only` is `False` the moment the commit's diff to `path` removes any line.
    """
    diff = _git(root, "diff", "--unified=0", f"{commit}^", commit, "--", path)
    removed = [
        line for line in diff.splitlines() if line.startswith("-") and not line.startswith("---")
    ]
    starts = [
        int(match.group(1)) for line in diff.splitlines() if (match := _HUNK_HEADER_RE.match(line))
    ]
    return not removed, starts


def _last_amendment_heading_line(root: Path, commit: str, path: str) -> int | None:
    content = _git(root, "show", f"{commit}:{path}")
    last: int | None = None
    for line_no, line in enumerate(content.splitlines(), start=1):
        if line.strip().startswith(_AMENDMENT_HEADING_PREFIX):
            last = line_no
    return last


def _adr_exists_in_range(root: Path, rev_range: str) -> bool:
    output = _git(root, "log", "--format=", "--name-only", rev_range, "--", "docs/ADR/")
    return any(name.startswith("docs/ADR/ADR-") for name in output.splitlines() if name)


def _check_gb501(root: Path, artifacts: list[str]) -> list[str]:
    """GB-501: recovery-before-fit. Vacuous (no errors) when no artifact exists."""
    if not artifacts:
        return []

    errors: list[str] = []
    recovery_commit = first_commit_adding(RECOVERY_REPORT_PATH, root)
    if recovery_commit is None:
        return [
            f"GB-501: {len(artifacts)} Layer R artifact(s) present but "
            f"{RECOVERY_REPORT_PATH} was never added -- the model was never proven "
            "on truth before this artifact exists"
        ]

    for artifact in artifacts:
        artifact_commit = first_commit_adding(artifact, root)
        if artifact_commit is None or not _is_ancestor(root, recovery_commit, artifact_commit):
            errors.append(
                f"GB-501: {RECOVERY_REPORT_PATH}'s first-add commit ({recovery_commit}) "
                f"is not an ancestor of {artifact}'s first-add commit -- Layer R was "
                "fit before Layer P was proven on truth"
            )
    return errors


def _check_gb502(root: Path, artifacts: list[str]) -> list[str]:
    """GB-502: prior-freeze-before-fit, plus the standing post-freeze invariants.

    (c) and (d) below apply whenever the freeze tag exists, independent of whether
    any Layer R artifact has landed yet -- priors can freeze before the first fit.
    """
    errors: list[str] = []
    tag_exists = _tag_exists(root, FREEZE_TAG)

    if artifacts and not tag_exists:
        errors.append(
            f"GB-502: {len(artifacts)} Layer R artifact(s) present but the "
            f"'{FREEZE_TAG}' tag does not exist -- priors were never frozen before "
            "fitting"
        )

    if not tag_exists:
        return errors

    freeze_commit = _tag_commit(root, FREEZE_TAG)

    for artifact in artifacts:
        artifact_commit = first_commit_adding(artifact, root)
        if artifact_commit is None or not _is_ancestor(root, freeze_commit, artifact_commit):
            errors.append(
                f"GB-502: the '{FREEZE_TAG}' tag ({freeze_commit}) is not an ancestor "
                f"of {artifact}'s first-add commit -- priors were not frozen before "
                "this artifact was fit"
            )

    post_freeze_priors_changes = _commits_touching(root, f"{freeze_commit}..HEAD", PRIORS_REAL_PATH)
    if post_freeze_priors_changes:
        errors.append(
            f"GB-502: {PRIORS_REAL_PATH} was modified after the '{FREEZE_TAG}' freeze "
            f"commit ({freeze_commit}) by commit(s) {post_freeze_priors_changes} -- "
            "frozen priors never change after the freeze"
        )

    amendment_commits = _commits_touching(root, f"{freeze_commit}..HEAD", PRIOR_ELICITATION_PATH)
    for commit in amendment_commits:
        append_only, hunk_starts = _diff_is_append_only(root, commit, PRIOR_ELICITATION_PATH)
        if not append_only:
            errors.append(
                f"GB-502: commit {commit} removes line(s) from {PRIOR_ELICITATION_PATH} "
                "after the freeze -- a post-freeze amendment must be append-only"
            )
            continue
        if not hunk_starts:
            continue
        heading_line = _last_amendment_heading_line(root, commit, PRIOR_ELICITATION_PATH)
        if heading_line is None or any(start < heading_line for start in hunk_starts):
            errors.append(
                f"GB-502: commit {commit}'s addition to {PRIOR_ELICITATION_PATH} does "
                f"not fall under a '{_AMENDMENT_HEADING_PREFIX}' heading"
            )
    if amendment_commits and not _adr_exists_in_range(root, f"{freeze_commit}..HEAD"):
        errors.append(
            f"GB-502: post-freeze change(s) to {PRIOR_ELICITATION_PATH} found "
            f"({amendment_commits}) with no ADR landing in the same commit range"
        )

    return errors


class _UsageError(Exception):
    """Raised by `_ArgParser.error` instead of calling `sys.exit` directly, so
    `main()` stays a plain argv -> exit-code function with a single process-exit
    call site (the module's own `__main__` guard)."""


class _ArgParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # type: ignore[override]
        raise _UsageError(message)


def _build_arg_parser() -> _ArgParser:
    parser = _ArgParser(
        prog="check_layer_order.py",
        description="GB-501/GB-502 git-ancestry check (SPEC-09 section 5).",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Override the scanned repository root (default: the repository root).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse `argv`, run the GB-501/GB-502 predicate, print its result, and return
    the process exit code: 0 clean (including the pre-conditions-absent notice), 1
    violation(s) found, 2 usage error. Never calls `sys.exit` itself.
    """
    parser = _build_arg_parser()
    try:
        args = parser.parse_args(argv)
    except _UsageError as exc:
        print(parser.format_usage(), end="", file=sys.stderr)
        print(f"check_layer_order.py: error: {exc}", file=sys.stderr)
        return 2

    root = Path(args.root).resolve() if args.root else repo_root()
    artifacts = _existing_layer_r_artifacts(root)
    tag_exists = _tag_exists(root, FREEZE_TAG)

    if not artifacts and not tag_exists:
        print(
            "check_layer_order: no Layer R artifact matching "
            f"({', '.join(LAYER_R_GLOBS)}) and no '{FREEZE_TAG}' tag found -- nothing "
            "to check yet. Check ran, found nothing to do."
        )
        return 0

    errors = _check_gb501(root, artifacts) + _check_gb502(root, artifacts)

    if errors:
        print("check_layer_order: violation(s) found:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1

    print(
        f"check_layer_order: {len(artifacts)} Layer R artifact(s) checked against "
        "GB-501/GB-502 -- all ancestry claims hold."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
