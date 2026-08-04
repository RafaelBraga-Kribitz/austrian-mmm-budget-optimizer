"""Tests for `ambo.common.logging` (T-005).

Implements: EB-041
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterator

import pytest

from ambo.common.config import load_settings, repo_root
from ambo.common.logging import REDACTION_TOKEN, get_logger

# Fictional path — never a real developer value, per EB-041's own rule, honored even
# inside a test that exists to prove redaction.
FAKE_PRIVATE_DROP = "D:/private/ambo_drop_fake"


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
