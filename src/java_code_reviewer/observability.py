"""Run observability and failure classification helpers."""

import json
import logging
import re
import time
import uuid
from collections.abc import Callable

from .state.review_state import ErrorType, ReviewState, RunStatus

logger = logging.getLogger(__name__)


RECOVERABLE_ERRORS = {
    ErrorType.PROVIDER_RATE_LIMIT.value,
    ErrorType.PROVIDER_NETWORK_ERROR.value,
    ErrorType.DIFF_FETCH_ERROR.value,
    ErrorType.RAG_ERROR.value,
    ErrorType.LLM_ERROR.value,
    ErrorType.LLM_PARSE_ERROR.value,
    ErrorType.FEEDBACK_REJECTED.value,
    ErrorType.PATCH_FILE_READ_ERROR.value,
    ErrorType.PATCH_GENERATION_ERROR.value,
    ErrorType.PATCH_PUSH_ERROR.value,
    ErrorType.UNKNOWN_ERROR.value,
}

SECRET_PATTERNS = [
    (re.compile(r"(https://[^:/\s]+:)([^@\s]+)(@)", re.IGNORECASE), lambda m: f"{m.group(1)}***REDACTED***{m.group(3)}"),
    (re.compile(r"(?i)(token=|access_token=|private_token=)([^&\s]+)"), lambda m: f"{m.group(1)}***REDACTED***"),
    (re.compile(r"(?i)(authorization:\s*(?:token|bearer)\s+)([^\s]+)"), lambda m: f"{m.group(1)}***REDACTED***"),
]


def ensure_run_metadata(state: ReviewState) -> None:
    """Initialize observability fields on the review state."""
    state.setdefault("run_id", f"review_{uuid.uuid4().hex[:12]}")
    state.setdefault("status", RunStatus.RUNNING)
    state.setdefault("node_results", {})
    state.setdefault("errors", [])
    state.setdefault("recovery_actions", [])


def wrap_node(name: str, node_func: Callable[[ReviewState], ReviewState]) -> Callable[[ReviewState], ReviewState]:
    """Wrap a LangGraph node with timing, error capture, and structured logs."""

    def wrapped(state: ReviewState) -> ReviewState:
        ensure_run_metadata(state)
        state["current_node"] = name
        state["pending_recovery"] = False
        start = time.perf_counter()
        retry_count = _retry_count(state, name)

        _log_event(state, name, "node_started", retry_count=retry_count)

        try:
            result = node_func(state)
        except Exception as exc:
            result = state
            result["error"] = f"{name} failed: {str(exc)}"

        duration_ms = int((time.perf_counter() - start) * 1000)
        failure_message = _node_failure_message(result, name)

        if failure_message:
            error_type = classify_error(name, failure_message)
            result["failed_node"] = name
            result["failure_type"] = error_type
            result["failure_message"] = failure_message
            result["pending_recovery"] = True
            result.setdefault("errors", []).append(
                {
                    "node": name,
                    "error_type": error_type,
                    "message": failure_message,
                    "recoverable": error_type in RECOVERABLE_ERRORS,
                }
            )
            result.setdefault("node_results", {})[name] = {
                "status": "failed",
                "duration_ms": duration_ms,
                "retry_count": retry_count,
                "error_type": error_type,
                "error_message": failure_message,
            }
            _log_event(
                result,
                name,
                "node_failed",
                duration_ms=duration_ms,
                retry_count=retry_count,
                error_type=error_type,
                error_message=failure_message,
            )
            return result

        if name in {"planner", "reviewer", "feedback", "patch"}:
            result["repair_prompt"] = ""
        result.setdefault("node_results", {})[name] = {
            "status": "success",
            "duration_ms": duration_ms,
            "retry_count": retry_count,
        }
        _log_event(result, name, "node_succeeded", duration_ms=duration_ms, retry_count=retry_count)
        return result

    return wrapped


def classify_error(node: str, message: str) -> str:
    """Classify a node failure into a stable error category."""
    lower = message.lower()

    if node == "input" or "validation" in lower or "invalid pr url" in lower or "not in the allowed scope" in lower:
        return ErrorType.VALIDATION_ERROR.value
    if "401" in lower or "403" in lower or "authentication" in lower or "bad credentials" in lower:
        return ErrorType.PROVIDER_AUTH_ERROR.value
    if "404" in lower or "not found" in lower:
        return ErrorType.PROVIDER_NOT_FOUND.value
    if "rate limit" in lower or "429" in lower:
        return ErrorType.PROVIDER_RATE_LIMIT.value
    if "timeout" in lower or "timed out" in lower or "connection" in lower or "empty reply" in lower:
        return ErrorType.PROVIDER_NETWORK_ERROR.value
    if "diff" in lower:
        return ErrorType.DIFF_FETCH_ERROR.value
    if node == "context_retriever":
        return ErrorType.RAG_ERROR.value
    if "json" in lower or "parse" in lower:
        return ErrorType.LLM_PARSE_ERROR.value
    if node == "feedback" and "approved" in lower:
        return ErrorType.FEEDBACK_REJECTED.value
    if node == "patch" and "could not read pr files" in lower:
        return ErrorType.PATCH_FILE_READ_ERROR.value
    if node == "patch" and ("push" in lower or "git" in lower):
        return ErrorType.PATCH_PUSH_ERROR.value
    if node == "patch":
        return ErrorType.PATCH_GENERATION_ERROR.value
    if node in {"planner", "reviewer", "feedback"}:
        return ErrorType.LLM_ERROR.value
    if "escapes repository" in lower or "path" in lower:
        return ErrorType.SECURITY_ERROR.value
    return ErrorType.UNKNOWN_ERROR.value


def redact_secrets(message: object) -> str:
    """Redact common token patterns before storing, logging, or sending errors to LLMs."""
    redacted = str(message)
    for pattern, replacement in SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def mark_run_finished(state: ReviewState) -> ReviewState:
    """Set final run status if it has not already been finalized."""
    if state.get("status") in {RunStatus.FAILED, RunStatus.PARTIAL_SUCCESS}:
        return state
    if state.get("error"):
        state["status"] = RunStatus.FAILED
    elif state.get("patch_error"):
        state["status"] = RunStatus.PARTIAL_SUCCESS
    else:
        state["status"] = RunStatus.SUCCESS
    return state


def record_recovery(state: ReviewState, action: str, reason: str) -> None:
    """Append a recovery decision to state and update node result status."""
    node = state.get("failed_node", "unknown")
    retry_count = _retry_count(state, node)
    state.setdefault("recovery_actions", []).append(
        {
            "node": node,
            "action": action,
            "reason": reason,
            "retry_count": retry_count,
        }
    )
    if node in state.setdefault("node_results", {}):
        state["node_results"][node]["status"] = "retried" if action == "retry" else state["node_results"][node]["status"]
    _log_event(state, node, "recovery_selected", action=action, reason=reason, retry_count=retry_count)


def clear_failure(state: ReviewState) -> None:
    """Clear transient failure routing fields."""
    state.pop("failed_node", None)
    state.pop("failure_type", None)
    state.pop("failure_message", None)
    state["pending_recovery"] = False


def _node_failure_message(state: ReviewState, node: str) -> str:
    if node == "input" and state.get("validation_error"):
        return redact_secrets(state["validation_error"])
    if node == "patch" and state.get("patch_error"):
        return redact_secrets(state["patch_error"])
    return redact_secrets(state.get("error", ""))


def _retry_count(state: ReviewState, node: str) -> int:
    return sum(1 for action in state.get("recovery_actions", []) if action.get("node") == node)


def _log_event(state: ReviewState, node: str, event: str, **extra: object) -> None:
    payload = {
        "run_id": state.get("run_id"),
        "node": node,
        "event": event,
        "mode": state.get("mode").value if hasattr(state.get("mode"), "value") else state.get("mode"),
        "provider": state.get("provider"),
        "repo": f"{state.get('repo_owner', '')}/{state.get('repo_name', '')}".strip("/"),
        "pr_number": state.get("pr_number"),
    }
    payload.update(extra)
    logger.info(json.dumps(payload, ensure_ascii=False, default=str))
