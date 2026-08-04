"""Tests for `ambo.common.logging` (T-005).

Implements: EB-041
"""

from __future__ import annotations

import re
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from ambo.common.config import load_settings, repo_root
from ambo.common.logging import REDACTION_TOKEN, get_logger

# Fictional path — never a real developer value, per EB-041's own rule, honored even
# inside a test that exists to prove redaction. `config.py`'s `load_settings()`
# calls `Path(...).resolve()` on the raw env value, which is a no-op on an already-
# absolute path but prefixes the cwd onto a relative one. A drive-letter path
# (`D:/...`) is absolute on Windows but merely relative-looking on POSIX, so a
# fixed `D:/...` literal passed redaction on the Windows CI leg while silently
# failing it on the Linux leg (01-09 fix-forward). Branching on `sys.platform`
# keeps the fixture absolute -- and therefore the redaction path genuinely
# exercised -- on both.
FAKE_PRIVATE_DROP = (
    "D:/private/ambo_drop_fake" if sys.platform == "win32" else "/private/ambo_drop_fake"
)


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    """Every test starts and ends with a cold cache, so env changes are re-resolved."""
    load_settings.cache_clear()
    yield
    load_settings.cache_clear()


def _unique_logger_name() -> str:
    # A fresh name per test keeps each test's logger (and its handler, bound to this
    # test's capsys-patched stream) isolated from every other test in the session.
    return f"ambo.test.{uuid.uuid4().hex}"


def test_redaction_in_message(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("AMBO_PRIVATE_DROP", FAKE_PRIVATE_DROP)
    load_settings.cache_clear()

    logger = get_logger(_unique_logger_name())
    logger.warning(f"reading staged file from {FAKE_PRIVATE_DROP}/staged/file.csv")

    captured = capsys.readouterr()
    assert REDACTION_TOKEN in captured.err
    assert FAKE_PRIVATE_DROP.lower() not in captured.err.lower()


def test_redaction_in_args(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("AMBO_PRIVATE_DROP", FAKE_PRIVATE_DROP)
    load_settings.cache_clear()

    logger = get_logger(_unique_logger_name())
    logger.warning("reading staged file from %s/staged/file.csv", FAKE_PRIVATE_DROP)

    captured = capsys.readouterr()
    assert REDACTION_TOKEN in captured.err
    assert FAKE_PRIVATE_DROP.lower() not in captured.err.lower()


def test_redaction_in_exception_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """CR-02: `logger.exception(...)`'s rendered traceback naturally embeds a
    `FileNotFoundError`/`PermissionError` message raised while touching a file
    under the private drop -- that text must be redacted too, not just
    `record.msg`/`record.args`."""
    monkeypatch.setenv("AMBO_PRIVATE_DROP", FAKE_PRIVATE_DROP)
    load_settings.cache_clear()

    logger = get_logger(_unique_logger_name())
    try:
        raise OSError(f"could not open {FAKE_PRIVATE_DROP}/staged/file.csv")
    except OSError:
        logger.exception("failed while reading the staged file")

    captured = capsys.readouterr()
    assert REDACTION_TOKEN in captured.err
    assert FAKE_PRIVATE_DROP.lower() not in captured.err.lower()


def test_redaction_of_non_str_msg(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """CR-02: a `Path` (or any non-`str`) passed directly as `msg` bypasses the
    old `isinstance(value, str)` guard entirely -- it must be stringified and
    redacted, not returned unchanged."""
    monkeypatch.setenv("AMBO_PRIVATE_DROP", FAKE_PRIVATE_DROP)
    load_settings.cache_clear()

    logger = get_logger(_unique_logger_name())
    logger.warning(Path(f"{FAKE_PRIVATE_DROP}/staged/file.csv"))

    captured = capsys.readouterr()
    assert REDACTION_TOKEN in captured.err
    assert FAKE_PRIVATE_DROP.lower() not in captured.err.lower()


def test_non_str_arg_without_the_private_path_is_not_corrupted(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A non-`str` arg that never embeds the private path (e.g. a plain int used
    with a `%d` conversion) must still format correctly -- the CR-02 fallback to
    `str(value)` must not corrupt unrelated non-str args."""
    monkeypatch.setenv("AMBO_PRIVATE_DROP", FAKE_PRIVATE_DROP)
    load_settings.cache_clear()

    logger = get_logger(_unique_logger_name())
    logger.warning("processed %d row(s)", 5)

    captured = capsys.readouterr()
    assert "processed 5 row(s)" in captured.err
    assert REDACTION_TOKEN not in captured.err


def test_filter_is_noop_when_unset(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("AMBO_PRIVATE_DROP", raising=False)
    load_settings.cache_clear()

    logger = get_logger(_unique_logger_name())
    logger.warning("plain message, nothing private in it")

    captured = capsys.readouterr()
    assert "plain message, nothing private in it" in captured.err
    assert REDACTION_TOKEN not in captured.err


def test_fixed_format_is_applied(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("AMBO_PRIVATE_DROP", raising=False)
    load_settings.cache_clear()

    name = _unique_logger_name()
    logger = get_logger(name)
    logger.warning("format check")

    captured = capsys.readouterr()
    # LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
    pattern = (
        r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} WARNING " + re.escape(name) + r" format check$"
    )
    assert re.match(pattern, captured.err.strip())


def test_get_logger_twice_yields_one_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AMBO_PRIVATE_DROP", raising=False)
    load_settings.cache_clear()

    name = _unique_logger_name()
    first = get_logger(name)
    second = get_logger(name)

    assert first is second
    assert len(first.handlers) == 1


def test_get_logger_is_the_only_construction_pattern_in_src_ambo() -> None:
    src_root = repo_root() / "src" / "ambo"
    logging_module = src_root / "common" / "logging.py"

    offenders = [
        str(py_file)
        for py_file in src_root.rglob("*.py")
        if py_file != logging_module and "getLogger(" in py_file.read_text(encoding="utf-8")
    ]

    assert not offenders, f"logging.getLogger() called outside common/logging.py: {offenders}"


def test_no_direct_stdout_writes_in_src_ambo() -> None:
    src_root = repo_root() / "src" / "ambo"

    offenders = [
        str(py_file)
        for py_file in src_root.rglob("*.py")
        if re.search(r"\bprint\(", py_file.read_text(encoding="utf-8"))
    ]

    assert not offenders, f"print() found in src/ambo/ (use get_logger instead): {offenders}"
