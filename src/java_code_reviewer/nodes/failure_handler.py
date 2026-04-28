"""Failure handler node - choose bounded recovery actions."""

import json

from ..config import get_config
from ..llm.client import LLMClient
from ..observability import clear_failure, record_recovery
from ..state.review_state import ErrorType, RecoveryActionType, ReviewMode, ReviewState, RunStatus


MAX_NODE_RETRIES = {
    "crawler": 3,
    "planner": 1,
    "reviewer": 2,
    "feedback": 1,
    "patch": 1,
}

ALLOWED_ACTIONS = {
    "input": {RecoveryActionType.FAIL.value},
    "crawler": {RecoveryActionType.RETRY.value, RecoveryActionType.FAIL.value},
    "context_retriever": {RecoveryActionType.SKIP_NODE.value, RecoveryActionType.FAIL.value},
    "planner": {RecoveryActionType.RETRY.value, RecoveryActionType.SKIP_NODE.value, RecoveryActionType.FAIL.value},
    "reviewer": {
        RecoveryActionType.RETRY.value,
        RecoveryActionType.RETRY_WITH_REPAIR_PROMPT.value,
        RecoveryActionType.FALLBACK_AUDIT_ONLY.value,
        RecoveryActionType.FAIL.value,
    },
    "feedback": {
        RecoveryActionType.RETRY.value,
        RecoveryActionType.SKIP_NODE.value,
        RecoveryActionType.FALLBACK_AUDIT_ONLY.value,
        RecoveryActionType.FAIL.value,
    },
    "patch": {
        RecoveryActionType.RETRY.value,
        RecoveryActionType.RETRY_WITH_REPAIR_PROMPT.value,
        RecoveryActionType.FALLBACK_AUDIT_ONLY.value,
        RecoveryActionType.PARTIAL_SUCCESS.value,
        RecoveryActionType.FAIL.value,
    },
}


def failure_handler_node(state: ReviewState) -> ReviewState:
    """Select a safe recovery action for the latest failure."""
    failed_node = state.get("failed_node", "unknown")
    error_type = state.get("failure_type", ErrorType.UNKNOWN_ERROR.value)
    message = state.get("failure_message", "")
    retry_count = _retry_count(state, failed_node)

    action, reason = _default_recovery_action(state, failed_node, error_type, retry_count)

    llm_action, llm_reason, repair_prompt = _llm_recovery_advice(state, failed_node, error_type, message)
    if llm_action and _is_allowed(failed_node, llm_action) and _within_retry_budget(failed_node, llm_action, retry_count):
        action = llm_action
        reason = llm_reason or reason
        if action == RecoveryActionType.RETRY_WITH_REPAIR_PROMPT.value:
            state["repair_prompt"] = repair_prompt

    if not _is_allowed(failed_node, action):
        action, reason = RecoveryActionType.FAIL.value, f"Action {action} is not allowed for {failed_node}"

    record_recovery(state, action, reason)
    state["recovery_action"] = action

    if action in {RecoveryActionType.RETRY.value, RecoveryActionType.RETRY_WITH_REPAIR_PROMPT.value}:
        _clear_node_error(state, failed_node)
    elif action == RecoveryActionType.SKIP_NODE.value:
        _clear_node_error(state, failed_node)
        state.setdefault("node_results", {}).setdefault(
            failed_node,
            {"status": "skipped", "duration_ms": 0, "retry_count": retry_count},
        )
        state["node_results"][failed_node]["status"] = "skipped"
    elif action == RecoveryActionType.FALLBACK_AUDIT_ONLY.value:
        _clear_node_error(state, failed_node)
        state["mode"] = ReviewMode.AUDIT_ONLY
        state["route_decision"] = "report"
        state["status"] = RunStatus.PARTIAL_SUCCESS
    elif action == RecoveryActionType.PARTIAL_SUCCESS.value:
        state["route_decision"] = "report"
        state["status"] = RunStatus.PARTIAL_SUCCESS
        state.pop("error", None)
    else:
        state["status"] = RunStatus.FAILED

    if action in {RecoveryActionType.FAIL.value, RecoveryActionType.PARTIAL_SUCCESS.value, RecoveryActionType.FALLBACK_AUDIT_ONLY.value}:
        clear_failure(state)

    return state


def _default_recovery_action(
    state: ReviewState,
    failed_node: str,
    error_type: str,
    retry_count: int,
) -> tuple[str, str, str]:
    if error_type in {
        ErrorType.VALIDATION_ERROR.value,
        ErrorType.PROVIDER_AUTH_ERROR.value,
        ErrorType.PROVIDER_NOT_FOUND.value,
        ErrorType.SECURITY_ERROR.value,
    }:
        return RecoveryActionType.FAIL.value, f"{error_type} is not recoverable"

    if failed_node == "context_retriever":
        return RecoveryActionType.SKIP_NODE.value, "RAG failure can be skipped and reviewed with default prompt context"

    if failed_node == "planner":
        if _within_retry_budget(failed_node, RecoveryActionType.RETRY.value, retry_count):
            return RecoveryActionType.RETRY.value, "Planner failed with a recoverable error"
        return RecoveryActionType.SKIP_NODE.value, "Planner retry budget exhausted; continue without a plan"

    if failed_node in {"crawler", "reviewer", "feedback"}:
        if _within_retry_budget(failed_node, RecoveryActionType.RETRY.value, retry_count):
            return RecoveryActionType.RETRY.value, f"{failed_node} failed with a recoverable error"
        if failed_node == "feedback":
            return RecoveryActionType.FALLBACK_AUDIT_ONLY.value, "Feedback retry budget exhausted; disable autofix"
        return RecoveryActionType.FAIL.value, f"{failed_node} retry budget exhausted"

    if failed_node == "patch":
        if _within_retry_budget(failed_node, RecoveryActionType.RETRY.value, retry_count):
            return RecoveryActionType.RETRY.value, "Patch generation failed with a recoverable error"
        return RecoveryActionType.PARTIAL_SUCCESS.value, "Patch retry budget exhausted; keep audit report"

    if state.get("mode") == ReviewMode.AUTOFIX:
        return RecoveryActionType.FALLBACK_AUDIT_ONLY.value, "Unknown autofix failure; fall back to audit report"
    return RecoveryActionType.FAIL.value, "Unknown failure"


def _llm_recovery_advice(
    state: ReviewState,
    failed_node: str,
    error_type: str,
    message: str,
) -> tuple[str, str]:
    """Ask the LLM for a bounded recovery recommendation when it is useful."""
    if failed_node not in {"reviewer", "feedback", "patch"}:
        return "", "", ""
    if not get_config().llm_api_key:
        return "", "", ""

    prompt = f"""你是代码审查Agent的失败恢复顾问。
只能从以下动作中选择一个：{sorted(ALLOWED_ACTIONS.get(failed_node, []))}

失败节点：{failed_node}
错误类型：{error_type}
错误信息：{message}
当前模式：{state.get("mode")}

请只返回JSON对象：
{{
  "action": "retry|retry_with_repair_prompt|fallback_audit_only|skip_node|partial_success|fail",
  "reason": "简短原因",
  "repair_prompt": "当action为retry_with_repair_prompt时，给下游节点追加的简短提示"
}}"""

    try:
        response = LLMClient().invoke(
            [
                {"role": "system", "content": "你只输出合法JSON，不输出解释。"},
                {"role": "user", "content": prompt},
            ]
        )
        parsed = json.loads(_extract_json_object(response))
        action = parsed.get("action", "")
        reason = parsed.get("reason", "")
        repair_prompt = parsed.get("repair_prompt", "")
        return action, reason, repair_prompt
    except Exception:
        return "", "", ""


def _extract_json_object(response: str) -> str:
    start = response.find("{")
    end = response.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return "{}"
    return response[start : end + 1]


def _clear_node_error(state: ReviewState, failed_node: str) -> None:
    if failed_node == "input":
        state.pop("validation_error", None)
    elif failed_node == "patch":
        state.pop("patch_error", None)
    else:
        state.pop("error", None)
    state["pending_recovery"] = False


def _retry_count(state: ReviewState, node: str) -> int:
    return sum(1 for action in state.get("recovery_actions", []) if action.get("node") == node)


def _within_retry_budget(node: str, action: str, retry_count: int) -> bool:
    if action not in {RecoveryActionType.RETRY.value, RecoveryActionType.RETRY_WITH_REPAIR_PROMPT.value}:
        return True
    return retry_count < MAX_NODE_RETRIES.get(node, 0)


def _is_allowed(node: str, action: str) -> bool:
    return action in ALLOWED_ACTIONS.get(node, {RecoveryActionType.FAIL.value})
