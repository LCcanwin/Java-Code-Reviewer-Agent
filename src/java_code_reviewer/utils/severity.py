"""Severity level utilities."""

from ..state.review_state import Severity


def severity_rank(severity: Severity) -> int:
    """Return numeric rank for severity sorting (lower = more severe)."""
    ranking = {
        Severity.BLOCKER: 0,
        Severity.CRITICAL: 1,
        Severity.WARNING: 2,
        Severity.INFO: 3,
    }
    return ranking.get(severity, 99)


def format_severity(severity: Severity) -> str:
    """Format severity for display."""
    labels = {
        Severity.BLOCKER: "BLOCKER",
        Severity.CRITICAL: "CRITICAL",
        Severity.WARNING: "WARNING",
        Severity.INFO: "INFO",
    }
    return labels.get(severity, "UNKNOWN")
