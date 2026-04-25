"""Unit tests for report_node."""

from java_code_reviewer.nodes.report_node import report_node
from java_code_reviewer.state.review_state import ReviewMode, ReviewState


def test_error_report_includes_failure_message():
    state: ReviewState = {
        "pr_url": "https://github.com/org/repo/pull/1",
        "mode": ReviewMode.AUDIT_ONLY,
        "validated": True,
        "provider": "github",
        "repo_owner": "org",
        "repo_name": "repo",
        "pr_number": 1,
        "diff_content": "",
        "changed_files": [],
        "pr_title": "Test PR",
        "pr_description": "",
        "retrieved_context": {},
        "issues": [],
        "route_decision": "report",
        "markdown_report": "",
        "error": "Review failed",
    }

    result = report_node(state)

    assert "Review failed: Review failed" in result["markdown_report"]
