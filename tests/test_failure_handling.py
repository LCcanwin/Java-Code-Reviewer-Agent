"""Unit tests for failure handling and recovery."""

from java_code_reviewer.main import run_review
from java_code_reviewer.nodes.failure_handler import failure_handler_node
from java_code_reviewer.observability import classify_error
from java_code_reviewer.state.review_state import ErrorType, ReviewMode, RunStatus


def test_classify_provider_auth_error():
    assert classify_error("crawler", "Failed to fetch PR: 403 Bad credentials") == ErrorType.PROVIDER_AUTH_ERROR.value


def test_failure_handler_falls_back_for_patch_failure_after_retry_budget():
    state = {
        "mode": ReviewMode.AUTOFIX,
        "failed_node": "patch",
        "failure_type": ErrorType.PATCH_GENERATION_ERROR.value,
        "failure_message": "Patch generation failed",
        "route_decision": "patch",
        "recovery_actions": [
            {
                "node": "patch",
                "action": "retry",
                "reason": "first retry",
                "retry_count": 0,
            }
        ],
        "node_results": {},
        "errors": [],
    }

    result = failure_handler_node(state)

    assert result["recovery_action"] == "partial_success"
    assert result["route_decision"] == "report"
    assert result["status"] == RunStatus.PARTIAL_SUCCESS
    assert result["recovery_actions"][-1]["action"] == "partial_success"


def test_run_review_invalid_url_records_failed_status_and_report():
    result = run_review("not-a-url")

    assert result["status"] == RunStatus.FAILED
    assert result["errors"][0]["error_type"] == ErrorType.VALIDATION_ERROR.value
    assert "Validation failed" in result["markdown_report"]
