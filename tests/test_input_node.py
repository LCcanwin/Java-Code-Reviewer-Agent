"""Unit tests for input_node."""

import pytest

from java_code_reviewer.nodes.input_node import check_scope_limit, parse_pr_url
from java_code_reviewer.state.review_state import ReviewMode, ReviewState
from java_code_reviewer.main import compile_graph


class TestParsePrUrl:
    def test_github_url_parsed(self):
        provider, owner, repo, pr_number = parse_pr_url(
            "https://github.com/alibaba/fastjson/pull/1234"
        )
        assert provider == "github"
        assert owner == "alibaba"
        assert repo == "fastjson"
        assert pr_number == 1234

    def test_gitlab_url_parsed(self):
        provider, owner, repo, pr_number = parse_pr_url(
            "https://gitlab.com/myorg/myrepo/-/merge_requests/42"
        )
        assert provider == "gitlab"
        assert owner == "myorg"
        assert repo == "myrepo"
        assert pr_number == 42

    def test_gitlab_nested_group_url_parsed(self):
        provider, owner, repo, pr_number = parse_pr_url(
            "https://gitlab.com/platform/backend/myrepo/-/merge_requests/42/diffs"
        )
        assert provider == "gitlab"
        assert owner == "platform/backend"
        assert repo == "myrepo"
        assert pr_number == 42

    def test_invalid_url_returns_none(self):
        provider, owner, repo, pr_number = parse_pr_url("not-a-url")
        assert provider is None
        assert owner == ""
        assert repo == ""
        assert pr_number == 0


class TestInputNode:
    def test_invalid_url_sets_validation_error(self):
        state: ReviewState = {
            "pr_url": "not-a-url",
            "mode": ReviewMode.AUDIT_ONLY,
            "validated": False,
            "provider": "github",
            "repo_owner": "",
            "repo_name": "",
            "pr_number": 0,
            "diff_content": "",
            "changed_files": [],
            "pr_title": "",
            "pr_description": "",
            "retrieved_context": {},
            "issues": [],
            "route_decision": "report",
            "markdown_report": "",
        }

        from java_code_reviewer.nodes.input_node import input_node

        result = input_node(state)
        assert result["validated"] is False
        assert "validation_error" in result


class TestCheckScopeLimit:
    def test_empty_scope_allows_all(self):
        assert check_scope_limit("any", "owner", "repo") is True
