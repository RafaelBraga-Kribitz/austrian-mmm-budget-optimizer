"""The project's typed exception hierarchy (EB-040).

Implements: EB-040

Every module that raises a domain error subclasses `AmboError` — never a bare
`Exception` or a built-in exception type for an expected failure condition
(09_ANTI_PATTERNS section A-7). `AmboError` is the root; `ConfigError` is the first
subclass, raised by `ambo.common.config`. Later modules add their own subclasses as
they land, each getting its own `docs/MODULE_CONTRACTS.md` entry.
"""

from __future__ import annotations


class AmboError(Exception):
    """The project's root exception.

    Invariant: no `AmboError` (or subclass) message may ever contain private-drop
    content or a private-drop path (EB-041). A failure that would need the path to
    be understandable reports the path's role — e.g. "the private drop path" — never
    its value. Redaction of already-emitted log records is the logging filter's job;
    this invariant governs what code may put into a message in the first place.
    """


class ConfigError(AmboError):
    """Raised by `ambo.common.config` on invalid or missing configuration."""


class SimulationError(AmboError):
    """Raised by every module in `src/ambo/simulate/` (SPEC-01) for: a missing or
    invalid scenario YAML, an out-of-domain math input, a missing season-window row,
    and a failed decomposition audit. Inherits the redaction invariant above
    unchanged — a `SimulationError` message never contains private-drop content or
    path, exactly like every other `AmboError` subclass (no simulate-layer input is
    ever private, but the invariant is stated once on the root and holds for free)."""


class DataContractError(AmboError):
    """Raised by `ambo.common.db` (03_MODULES section 1.3), the only data doorway for
    model/decide/report code (AD-030), for: a missing warehouse file (message directs
    the caller to run the `transform` make target), an unknown layer argument, a
    mart-schema mismatch against the declared column contract, and a violated frame
    postcondition. Inherits the redaction invariant above unchanged — warehouse data
    is Layer P and never private today, but plan 03-06's fake Layer R fixture and
    Phase 6's real anonymized data mean a `DataContractError` message must never
    carry private-drop content or path, exactly like every other `AmboError`
    subclass."""


class FitError(AmboError):
    """Raised by `src/ambo/model/` (SPEC-04) for: an all-zero channel that cannot
    be scaled, a requested channel missing from the input frame, invalid transform
    domain (L < 1, non-finite scale factors), and later sampler/posterior I/O
    failures. Inherits the redaction invariant on `AmboError` unchanged."""


class ValidationError(AmboError):
    """Raised by `src/ambo/validate/` (SPEC-05) for: an unknown layer name, a
    missing truth file or posterior, a malformed recovery-gate YAML, or a
    zero-spend channel that would make average ROAS 0/0. Inherits the redaction
    invariant on `AmboError` unchanged."""
