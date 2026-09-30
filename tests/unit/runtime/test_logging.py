import json
import logging
from pathlib import Path

from fedsira.domain.enums import FailureClass, RuntimeComponentName, WorkflowTerminalState
from fedsira.runtime import (
    configure_structured_file_logging,
    get_structured_logger,
    log_workflow_terminal,
)


def test_get_structured_logger_emits_json_lines() -> None:
    logger = get_structured_logger(RuntimeComponentName.DOCTOR)
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
    first = get_structured_logger(RuntimeComponentName.ANCHOR_TRAINING)
    second = get_structured_logger(RuntimeComponentName.ANCHOR_TRAINING)
    assert first is second
    assert len(first.handlers) == 1


def test_get_structured_logger_never_becomes_scientific_evidence_source() -> None:
    logger = get_structured_logger(RuntimeComponentName.EXECUTION)
    assert logger.propagate is False


def test_structured_file_logging_persists_json_line(tmp_path: Path) -> None:
    logger = get_structured_logger(RuntimeComponentName.ARTIFACTS)
    log_path = tmp_path / "experiment.log"
    configure_structured_file_logging(logger, log_path)
    logger.info("cell completed")
    assert json.loads(log_path.read_text(encoding="utf-8"))["message"] == "cell completed"


def test_workflow_terminal_event_has_typed_status_and_bounded_failure_message(
    tmp_path: Path,
) -> None:
    logger = get_structured_logger(RuntimeComponentName.REPORTING)
    log_path = tmp_path / "reporting.log"
    configure_structured_file_logging(logger, log_path)

    log_workflow_terminal(
        logger,
        RuntimeComponentName.CREATING_REPORT,
        WorkflowTerminalState.BLOCKED,
        FailureClass.EVIDENCE_INSUFFICIENT,
        "x" * 300,
    )

    payload = json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
    assert payload["message"] == "workflow.terminal"
    assert payload["workflow"] == RuntimeComponentName.CREATING_REPORT
    assert payload["state"] == WorkflowTerminalState.BLOCKED
    assert payload["failure_class"] == FailureClass.EVIDENCE_INSUFFICIENT
    assert len(payload["failure_message"]) == 256
