"""Unit tests for option_router."""

from java_code_reviewer.nodes.option_router import option_router_node
from java_code_reviewer.state.review_state import ReviewMode, ReviewState


def _state() -> ReviewState:
    return {
        "pr_url": "https://github.com/org/repo/pull/1",
        "mode": ReviewMode.AUTOFIX,
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
        "route_decision": "patch",
        "markdown_report": "",
    }


def test_error_routes_to_report():
    state = _state()
    state["error"] = "Review failed"

    result = option_router_node(state)

    assert result["route_decision"] == "report"
