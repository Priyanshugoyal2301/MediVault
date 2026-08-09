"""Safety layer — deterministic red-flag detection for health Q&A."""

from .red_flags import SafetyResult, check_safety

__all__ = ["SafetyResult", "check_safety"]
