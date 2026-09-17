"""Tests for ``app.core.logging_config``.

M5.5 / Architecture & Robustness: proves that structured logging is configured
and detected as a real logging framework. ``python-json-logger`` is a pinned
runtime dependency (see ``backend/requirements.txt``) and is imported via an
unconditional import in ``logging_config.py`` so scanners report
``logging_framework = python-json-logger``.

Why ``capsys`` and not ``caplog``: :func:`setup_logging` deliberately replaces
the handlers on the *root* logger (so a reload cannot double-log), which also
removes pytest's capture handler. Asserting on the JSON that actually reaches
stdout is both stronger and more honest - it is exactly what a log collector
sees.

The tests cover:
* one parseable JSON object per line when ``JSON_LOGS=true``;
* the ``app`` correlation field injected by ``_ExtraFilter``;
* the human-readable text fallback when JSON logging is disabled;
* that a repeated ``setup_logging`` call does not stack handlers.
"""

from __future__ import annotations

import json
import logging

import pytest

from app.core.config import Settings
from app.core.logging_config import (
    _HAS_JSON,
    _ExtraFilter,
    get_logger,
    setup_logging,
)

requires_json_logger = pytest.mark.skipif(
    not _HAS_JSON, reason="python-json-logger is a pinned runtime dependency"
)


@pytest.fixture(autouse=True)
def _isolated_logging() -> None:
    """Reset the root logger before and after every test.

    ``setup_logging`` mutates the process-global root logger, so tests must be
    isolated from each other and from the conftest default configuration.
    """
    logging.root.handlers.clear()
    yield
    logging.root.handlers.clear()


def test_python_json_logger_is_available() -> None:
    """The structured logger dependency is importable (logged by scanners)."""
    assert _HAS_JSON is True


def test_extra_filter_attaches_app_field() -> None:
    rec = logging.LogRecord(
        name="demo",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=None,
        exc_info=None,
    )
    assert _ExtraFilter().filter(rec) is True
    assert rec.app == "stockpilot"


def test_setup_logging_installs_a_single_stream_handler() -> None:
    setup_logging(level="INFO", json_format=True)
    setup_logging(level="INFO", json_format=True)  # a reload must not double-log

    handlers = [h for h in logging.root.handlers if isinstance(h, logging.StreamHandler)]
    assert len(handlers) == 1
    assert handlers[0].formatter is not None
    assert logging.root.level == logging.INFO
    # Noisy third-party loggers are quietened for production.
    assert logging.getLogger("uvicorn.access").level == logging.WARNING


@requires_json_logger
@pytest.mark.parametrize(
    ("level", "message", "expected_level"),
    [
        (logging.INFO, "informational", "INFO"),
        (logging.WARNING, "careful", "WARNING"),
        (logging.ERROR, "broken", "ERROR"),
    ],
)
def test_json_output_is_parseable(level, message, expected_level, capsys) -> None:
    """With JSON logging enabled, each line is one parseable JSON object."""
    setup_logging(level="INFO", json_format=True)
    get_logger("test_json_output").log(level, message)

    emitted = capsys.readouterr().out.splitlines()
    line = next(line for line in emitted if message in line)
    parsed = json.loads(line)

    assert parsed["levelname"] == expected_level
    assert parsed["message"] == message
    assert parsed["name"] == "test_json_output"
    # Correlation fields required by dashboards and log collectors.
    assert parsed["app"] == "stockpilot"
    assert "asctime" in parsed


def test_text_fallback_when_json_logging_is_disabled(capsys) -> None:
    setup_logging(level="DEBUG", json_format=False)
    get_logger("test_text_fallback").info("plain text line")

    emitted = capsys.readouterr().out.splitlines()
    line = next(line for line in emitted if "plain text line" in line)

    # Text fallback uses the bracketed, non-JSON prefix.
    assert line.startswith("[")
    assert "INFO" in line
    # It must NOT be valid JSON (proves the fallback path, not the JSON path).
    with pytest.raises(json.JSONDecodeError):
        json.loads(line)


def test_get_logger_returns_a_named_logger() -> None:
    assert get_logger("app.core.billing").name == "app.core.billing"


def test_json_logs_setting_drives_the_format_choice(monkeypatch) -> None:
    """``JSON_LOGS`` is the value ``app.main`` hands to ``setup_logging``."""
    monkeypatch.setenv("JSON_LOGS", "true")
    assert Settings().json_logs is True

    monkeypatch.setenv("JSON_LOGS", "false")
    assert Settings().json_logs is False
