"""Unit tests for crawler_node."""

import importlib
from unittest.mock import patch

from java_code_reviewer.agents.base import PRMetadata
from java_code_reviewer.state.review_state import ReviewMode

crawler_node_module = importlib.import_module("java_code_reviewer.nodes.crawler_node")


def test_crawler_node_errors_when_changed_files_have_empty_diff():
    state = {
        "pr_url": "https://github.com/org/repo/pull/1",
        "mode": ReviewMode.AUDIT_ONLY,
        "validated": True,
        "provider": "github",
        "repo_owner": "org",
        "repo_name": "repo",
        "pr_number": 1,
        "diff_content": "",
        "changed_files": [],
        "pr_title": "",
        "pr_description": "",
        "retrieved_context": {},
        "issues": [],
        "route_decision": "report",
        "markdown_report": "",
    }

    metadata = PRMetadata(
        repo_owner="org",
        repo_name="repo",
        pr_number=1,
        title="Test PR",
        description="",
        diff_content="",
        changed_files=["src/Example.java"],
        base_branch="main",
        head_branch="feature",
        head_repo_owner="org",
        head_repo_name="repo",
    )

    with patch.object(crawler_node_module, "GitHubAgent") as agent_cls:
        agent_cls.return_value.fetch_pr_metadata.return_value = metadata

        result = crawler_node_module.crawler_node(state)

    assert "diff content is empty" in result["error"]
    assert result["changed_files"] == []
