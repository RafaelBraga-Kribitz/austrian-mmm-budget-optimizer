# Canonical local interface (SPEC-08 §5, subset for this package).
SHELL := /bin/sh
.SHELLFLAGS := -ec

.PHONY: lint test simulate layer_p report

lint:
	uv run ruff check .

test:
	uv run pytest -m "not slow"

simulate:
	uv run python -m ambo.run simulate

layer_p:
	uv run python -m ambo.run layer_p

report:
	uv run python -m ambo.run report
