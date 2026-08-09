"""
shared-utils/logging.py

Provides a configured logger that redacts known health-data fields before
emitting any log record.

MANDATORY: all services MUST use get_logger() from this module for any code
path that touches user health data. Never use stdlib logging.getLogger()
directly in health-data-handling code — it will not redact.

Per 04_AGENT_RULES.md §4:
  "Do not log or print raw health data (report values, user answers)
   to application logs. Redact before logging."
"""

import logging
import os
import re
from typing import Any

# ---------------------------------------------------------------------------
# Fields that must never appear in logs.
# Extend this list as new sensitive fields are introduced.
# ---------------------------------------------------------------------------
_SENSITIVE_FIELD_PATTERNS: list[str] = [
    r'"value"\s*:\s*"[^"]*"',           # JSON: "value": "..."
    r'"unit"\s*:\s*"[^"]*"',            # JSON: "unit": "..."
    r'"reference_range[^"]*"\s*:\s*"[^"]*"',  # JSON: "reference_range*": "..."
    r'"hashed_password"\s*:\s*"[^"]*"', # JSON: "hashed_password": "..."
    r'"password"\s*:\s*"[^"]*"',        # JSON: "password": "..."
]

_REDACT_RE = re.compile(
    "|".join(_SENSITIVE_FIELD_PATTERNS),
    flags=re.IGNORECASE,
)

_REDACT_PLACEHOLDER = '"<REDACTED>"'


def _redact(message: str) -> str:
    """Replace sensitive field values with a redaction placeholder."""
    return _REDACT_RE.sub(_REDACT_PLACEHOLDER, message)


class _RedactingFilter(logging.Filter):
    """Logging filter that redacts sensitive fields from log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        record.msg = _redact(str(record.msg))
        if record.args:
            # Stringify args so we can redact, then clear args to avoid
            # double-format issues.
            record.msg = _redact(record.msg % record.args)
            record.args = ()
        return True


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger with redaction enabled and level from LOG_LEVEL env var.

    Usage:
        from packages.shared_utils.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Processed report for user_id=%s", user_id)  # safe
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%SZ",
            )
        )
        logger.addHandler(handler)

    logger.addFilter(_RedactingFilter())

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    return logger
