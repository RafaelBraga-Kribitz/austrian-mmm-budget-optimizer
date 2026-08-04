"""The sole logger factory for the project (EB-041).

Implements: EB-041

`get_logger(__name__)` is the only sanctioned logger-construction pattern in
`src/ambo/`: no module calls `logging.getLogger` directly, and `src/` contains no
direct standard-output writes (`print`). The format string this module applies is
fixed project-wide, since downstream log parsing depends on it.
"""

from __future__ import annotations

import logging
import os

from ambo.common.config import load_settings

# Fixed structured format: timestamp, level name, logger name, message. Downstream
# log parsing depends on this shape not changing per module.
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

# The environment variable that sets the logger's level; defaults to INFO when unset
# or invalid.
AMBO_LOG_LEVEL_ENV_VAR = "AMBO_LOG_LEVEL"

REDACTION_TOKEN = "<PRIVATE_DROP>"


def _redact_case_insensitive(haystack: str, needle: str, replacement: str) -> str:
    """Replace every case-insensitive occurrence of `needle` in `haystack`.

    Plain `str.replace` is case-sensitive, which is not sufficient on Windows where
    the same path can be typed with any letter case. Matching is done manually
    (rather than via `re`) so an arbitrary filesystem path never needs escaping into
    a regex pattern.
    """
    if not needle:
        return haystack
    result: list[str] = []
    lower_haystack = haystack.lower()
    lower_needle = needle.lower()
    needle_len = len(needle)
    i = 0
    while i < len(haystack):
        if lower_haystack[i : i + needle_len] == lower_needle:
            result.append(replacement)
            i += needle_len
        else:
            result.append(haystack[i])
            i += 1
    return "".join(result)


class PrivatePathFilter(logging.Filter):
    """Redacts the resolved `AMBO_PRIVATE_DROP` path from every emitted record.

    Reads the resolved path from `load_settings().private_drop` — never from the
    environment directly — so there is exactly one resolution path (EB-041). When
    `private_drop` is `None` the filter is a pass-through no-op. When it is set, every
    occurrence of the resolved path is replaced by `<PRIVATE_DROP>` in `record.msg`
    and every element of `record.args`, matched case-insensitively and with both
    Windows and POSIX separator forms normalized. This is redact-and-emit, not
    drop-and-raise: the record is still emitted, with the path removed.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        private_drop = load_settings().private_drop
        if private_drop is None:
            return True

        raw = str(private_drop)
        needles = {raw, raw.replace("\\", "/"), raw.replace("/", "\\")}

        def _redact(value: object) -> object:
            if not isinstance(value, str):
                return value
            redacted = value
            for needle in needles:
                redacted = _redact_case_insensitive(redacted, needle, REDACTION_TOKEN)
            return redacted

        record.msg = _redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {key: _redact(val) for key, val in record.args.items()}
            else:
                record.args = tuple(_redact(arg) for arg in record.args)
        return True


def get_logger(name: str) -> logging.Logger:
    """Return a configured `logging.Logger` for `name`.

    `PrivatePathFilter` and a `LOG_FORMAT`-formatted `StreamHandler` are attached
    exactly once per logger, regardless of how many times this is called for the same
    `name`. The level is read from `AMBO_LOG_LEVEL` (default `INFO`); an unset or
    invalid value falls back to `INFO` rather than raising. `name` is conventionally
    `__name__` of the caller.
    """
    logger = logging.getLogger(name)

    already_configured = any(
        isinstance(existing_filter, PrivatePathFilter) for existing_filter in logger.filters
    )
    if not already_configured:
        logger.addFilter(PrivatePathFilter())
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)
        # This logger's own handler is the sole sink for its records; propagating to
        # ancestor loggers (which may carry their own handler from another
        # get_logger() call) would otherwise double-emit every record.
        logger.propagate = False

    level_name = os.environ.get(AMBO_LOG_LEVEL_ENV_VAR, "INFO")
    level = logging.getLevelName(level_name)
    logger.setLevel(level if isinstance(level, int) else logging.INFO)

    return logger
