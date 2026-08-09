"""
shared-utils — public API

ONLY get_logger is exported from this package.

All services must import the logger as:

    from packages.shared_utils import get_logger
    logger = get_logger(__name__)

Do NOT import stdlib logging directly in any file that handles health data:

    import logging          # ← wrong — no redaction
    logging.getLogger(...)  # ← wrong — no redaction

The redacting filter in get_logger() ensures health-data fields are stripped
before any log record is emitted (04_AGENT_RULES.md §4).

If you genuinely need raw stdlib logging (e.g. for a non-health ops script),
import it explicitly from the stdlib with a comment explaining why it's safe.
"""

from .logging import get_logger

__all__ = ["get_logger"]
