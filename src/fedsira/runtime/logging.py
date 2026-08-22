import json
import logging
from typing import ClassVar

from fedsira.domain.records import CanonicalToken

LOGGER_NAME_PREFIX = "fedsira"


class StructuredJsonFormatter(logging.Formatter):
    RESERVED_ATTRIBUTES: ClassVar[frozenset[str]] = frozenset(
        logging.LogRecord("", 0, "", 0, "", (), None).__dict__
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRIBUTES:
                payload[key] = value
        return json.dumps(payload, sort_keys=True, default=str)


def get_structured_logger(component: CanonicalToken) -> logging.Logger:
    logger = logging.getLogger(f"{LOGGER_NAME_PREFIX}.{component}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger
