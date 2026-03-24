"""Unit tests for review_state."""

import pytest

from java_code_reviewer.state.review_state import Issue, ReviewMode, ReviewState, Severity


class TestReviewState:
    def test_state_has_required_fields(self):
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
        }

        assert state["validated"] is True
        assert state["mode"] == ReviewMode.AUDIT_ONLY


class TestIssue:
    def test_issue_dict_structure(self):
        issue: Issue = {
            "severity": Severity.BLOCKER,
            "rule_id": "NAMING-001",
            "file_path": "src/Example.java",
            "line_number": 10,
            "message": "Test violation",
            "code_snippet": "public class example {}",
        }
        assert issue["severity"] == Severity.BLOCKER
        assert issue["rule_id"] == "NAMING-001"


class TestSeverity:
    def test_severity_order(self):
        order = [Severity.BLOCKER, Severity.CRITICAL, Severity.WARNING, Severity.INFO]
        assert order[0] == Severity.BLOCKER
        assert order[-1] == Severity.INFO
