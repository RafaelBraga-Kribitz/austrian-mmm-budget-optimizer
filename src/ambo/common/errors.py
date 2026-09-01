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
