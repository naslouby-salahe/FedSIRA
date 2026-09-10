import json
import logging
from pathlib import Path

from fedsira.runtime import configure_structured_file_logging, get_structured_logger


def test_get_structured_logger_emits_json_lines() -> None:
    logger = get_structured_logger("test-component")
    handler = logger.handlers[0]
    assert handler.formatter is not None

    record = logging.LogRecord(
        name=logger.name,
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    payload = json.loads(handler.formatter.format(record))
    assert payload["message"] == "hello"
    assert payload["component"] == logger.name
    assert payload["level"] == "INFO"


def test_get_structured_logger_reuses_handler_on_repeated_calls() -> None:
    first = get_structured_logger("idempotent-component")
    second = get_structured_logger("idempotent-component")
    assert first is second
    assert len(first.handlers) == 1


def test_get_structured_logger_never_becomes_scientific_evidence_source() -> None:
    logger = get_structured_logger("evidence-component")
    assert logger.propagate is False


def test_structured_file_logging_persists_json_line(tmp_path: Path) -> None:
    logger = get_structured_logger("file-component")
    log_path = tmp_path / "experiment.log"
    configure_structured_file_logging(logger, log_path)
    logger.info("cell completed")
    assert json.loads(log_path.read_text(encoding="utf-8"))["message"] == "cell completed"
