# =============================================================================
# AMBO — canonical build interface (SPEC-08 section 5, EB-050)
# =============================================================================
#
# Portable POSIX-sh shell pin (RESEARCH.md Pattern 1,
# .planning/phases/01-repository-foundation/01-RESEARCH.md). GNU Make normally never
# takes SHELL from the caller's environment — except on Windows, where it explicitly
# does, since most Windows users never set it themselves. Pinning SHELL to the literal
# path /bin/sh here overrides that on every platform: on Linux it resolves directly to
# the real shell; on native-Win32 GNU Make (the toolchain this repo targets — verified
# GNU Make 4.4.1 on this dev machine), when /bin/sh does not resolve as a Windows path,
# Make falls back to a PATH search for the shell's basename (`sh`, trying .exe/.com/
# .bat/.sh in turn) — documented native-Win32-Make behavior, not a hack — which finds
# Git's own sh.exe on PATH inside a Git Bash session. .SHELLFLAGS adds -eu (errexit +
# nounset) on top of the default -c, so a failing command inside a multi-command recipe
# line aborts that line (and therefore the target) instead of silently continuing.
SHELL := /bin/sh
.SHELLFLAGS := -eu -c

# The target list is closed: exactly the 18 names below, no more, no fewer (SPEC-08
# section 5), declared in the spec's own order. Do not add help/clean/format/ci or any
# other convenience target. .DEFAULT_GOAL is deliberately left unset — SPEC-08 section 5
# defines no `help` target, so there is nothing sensible to default to.
.PHONY: setup simulate validate-sim intake anonymize validate-intake transform \
        fit-synthetic fit-real recover sensitivity decide ssot export report \
        test lint all

# -----------------------------------------------------------------------------
# D-27 loud-failing stub. Every target whose owning phase has not arrived yet echoes
# this exact message (naming its phase) and exits non-zero, so a missing target can
# never report success by doing nothing (T-01-19 mitigation).
# -----------------------------------------------------------------------------
define STUB
	@echo "NOT IMPLEMENTED — arrives in Phase $(1) (see README §Roadmap)" && exit 1
endef

# EB-050: sampling targets print their expected runtime before anything else, ahead of
# the stub message — encoded now as variables so later phases fill in the behavior, not
# the contract. Ceiling is the SPEC-08 section 5 / MD-050 normative figure, 4 cores.
FIT_SYNTHETIC_RUNTIME := expected runtime: 3 fits (S-A, S-B, S-C), <=35 min/fit at MD-050 on 4 cores (SPEC-08 section 5)
FIT_REAL_RUNTIME      := expected runtime: 1 fit (Layer R, frozen priors), <=35 min/fit at MD-050 on 4 cores (SPEC-08 section 5)
SENSITIVITY_RUNTIME   := expected runtime: VR-501..504 sensitivity refits, <=35 min/fit each at MD-050 on 4 cores (SPEC-08 section 5)

# -----------------------------------------------------------------------------
# setup — real
# -----------------------------------------------------------------------------
setup:
	uv venv
	uv sync
	# `pre-commit install` per SPEC-08 section 5 verbatim. This is a no-op for anyone
	# who only reads the repository: the hook it installs fires exclusively on
	# `git commit`, never on a read-only clone or checkout.
	uv run pre-commit install

# -----------------------------------------------------------------------------
# simulate, validate-sim — real (Phase 2, T-108). validate-sim runs the in-process
# SIM-070..075 gate runner, then the BP-G-02 test selection (SIM-002's single home
# for the scenario-YAML-vs-SPEC-01 §4 check), joined so the target fails if either
# does — .SHELLFLAGS's errexit pin (top of file) already stops the recipe at the
# first failing line.
# -----------------------------------------------------------------------------
simulate:
	uv run python -m ambo.simulate all

validate-sim:
	uv run python -m ambo.simulate validate
	uv run pytest tests/unit/test_scenario_config.py -k "spec_parameter_table or rule_level" -q

# -----------------------------------------------------------------------------
# intake, anonymize, validate-intake — stubs (Phase 6)
# -----------------------------------------------------------------------------
intake:
	$(call STUB,6)

anonymize:
	$(call STUB,6)

validate-intake:
	$(call STUB,6)

# -----------------------------------------------------------------------------
# transform — real, unconditional (D-21, plan 03-01). The D-17 conditional this
# target used to carry existed only so CI job 3 could pass by running rather than
# being skipped while no dbt project existed yet (Phase 1 D-16); that purpose is
# spent now that dbt/dbt_project.yml is a real, committed project. A
# "nothing-to-build" branch here would let a deleted dbt_project.yml report a green
# CI job by finding nothing to do — the opposite of D-17's own loud-failure intent.
# dbt itself already fails loudly on a missing project, and
# tests/unit/test_repo_layout.py already asserts dbt/ against SPEC-08 section 2, so
# no conditional is needed to protect either invariant.
# -----------------------------------------------------------------------------
transform:
	uv run dbt build --project-dir dbt --profiles-dir dbt

# -----------------------------------------------------------------------------
# fit-synthetic — stub (Phase 4), sampling target
# -----------------------------------------------------------------------------
fit-synthetic:
	@echo "$(FIT_SYNTHETIC_RUNTIME)"
	$(call STUB,4)

# -----------------------------------------------------------------------------
# fit-real — stub (Phase 7), sampling target
# -----------------------------------------------------------------------------
fit-real:
	@echo "$(FIT_REAL_RUNTIME)"
	$(call STUB,7)

# -----------------------------------------------------------------------------
# recover — stub (Phase 5)
# -----------------------------------------------------------------------------
recover:
	$(call STUB,5)

# -----------------------------------------------------------------------------
# sensitivity — stub (Phase 7), sampling target
# -----------------------------------------------------------------------------
sensitivity:
	@echo "$(SENSITIVITY_RUNTIME)"
	$(call STUB,7)

# -----------------------------------------------------------------------------
# decide — stub (Phase 8)
# -----------------------------------------------------------------------------
decide:
	$(call STUB,8)

# -----------------------------------------------------------------------------
# ssot — stub (Phase 5)
# -----------------------------------------------------------------------------
ssot:
	$(call STUB,5)

# -----------------------------------------------------------------------------
# export — real (Phase 3, T-205). Registry-driven, byte-stable mart-to-CSV writer;
# see scripts/export_marts.py for the registry (D-03) and the atomic write (D-04).
# -----------------------------------------------------------------------------
export:
	uv run python scripts/export_marts.py

# -----------------------------------------------------------------------------
# report — stub (Phase 9)
# -----------------------------------------------------------------------------
report:
	$(call STUB,9)

# -----------------------------------------------------------------------------
# test — real. Smoke marker excluded by default; SMOKE=1 includes it. The fit marker
# is always deselected — full fits never run via `make test` (EB-061).
# -----------------------------------------------------------------------------
ifeq ($(SMOKE),1)
PYTEST_MARKER_EXPR := not fit
else
PYTEST_MARKER_EXPR := not smoke and not fit
endif

test:
	uv run pytest -m "$(PYTEST_MARKER_EXPR)"

# -----------------------------------------------------------------------------
# lint — real. Fixed order, first-failure-wins: ruff check, then ruff format --check,
# then mypy. Each recipe line below is its own make-spawned shell invocation, and
# make's default behavior already stops the target at the first line that fails; the
# .SHELLFLAGS errexit pin (top of file) reinforces the same first-failure semantics
# for any line that itself runs more than one command.
#
# `ruff format --check` is scoped to `src tests scripts` (plan 03-09), not `.`.
# `ruff check .` and `mypy` (pyproject.toml's `[tool.mypy] files = ["src/ambo"]`)
# are both already effectively scoped to this project's Python surface -- `ruff
# check` only lints .py/.pyi/.ipynb files regardless of the `.` argument, and
# mypy's own config pins `src/ambo`. `ruff format`, uniquely among the three, also
# walks Markdown files by default looking for fenced Python code blocks to
# reformat -- a real ruff feature, not a bug, but not this project's `lint`
# target's intent: the whole-repo `.` argument on this one line let ruff's
# formatter reach into `.planning/`'s narrative planning documents, which are not
# source code and were never meant to be held to the format target's style.
# Scoping this line to match the other two closes that gap rather than papering
# over a real failure -- `make lint` is unchanged in what it verifies about
# src/ambo, tests/, and scripts/.
# -----------------------------------------------------------------------------
lint:
	uv run ruff check .
	uv run ruff format --check src tests scripts
	uv run mypy

# -----------------------------------------------------------------------------
# all — real, BP-D-20 guard. Composite transform -> recover -> sensitivity -> decide
# -> ssot -> export -> report. Fails fast with instructions when required posteriors
# are absent, before any sub-target runs, and never triggers a fit itself.
# -----------------------------------------------------------------------------
POSTERIORS_DIR := data/posteriors

all:
	@if [ -z "$$(find $(POSTERIORS_DIR) -maxdepth 1 -name '*.parquet' -print -quit 2>/dev/null)" ]; then \
		echo "make all: no posteriors found under $(POSTERIORS_DIR) -- run 'make fit-synthetic' first (or 'make fit-real' for Layer R), then re-run 'make all'."; \
		exit 1; \
	fi
	$(MAKE) transform recover sensitivity decide ssot export report
