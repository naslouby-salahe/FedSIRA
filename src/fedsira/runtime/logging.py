import json
import logging
from typing import ClassVar

from fedsira.domain.records import RuntimeComponentName, TextValue

LOGGER_NAME_PREFIX = "fedsira"


class StructuredJsonFormatter(logging.Formatter):
    RESERVED_ATTRIBUTES: ClassVar[frozenset[str]] = frozenset(
        logging.LogRecord("", 0, "", 0, "", (), None).__dict__
    )

    def format(self, record: logging.LogRecord) -> TextValue:
        payload = record.__dict__.copy()
        for reserved_key in self.RESERVED_ATTRIBUTES:
            payload.pop(reserved_key, None)
        payload["timestamp"] = self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z")
        payload["level"] = record.levelname
        payload["component"] = record.name
        payload["message"] = record.getMessage()
        return json.dumps(payload, sort_keys=True, default=str)


def get_structured_logger(component: RuntimeComponentName) -> logging.Logger:
    logger = logging.getLogger(f"{LOGGER_NAME_PREFIX}.{component}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger
