"""Unit tests for LLM response parsing helpers."""

import importlib
from unittest.mock import patch

from java_code_reviewer.nodes.feedback_node import _parse_feedback_response
from java_code_reviewer.nodes.patch_node import _parse_patch_response
from java_code_reviewer.nodes.reviewer_node import _parse_issues
from java_code_reviewer.state.review_state import ReviewMode, Severity

reviewer_node_module = importlib.import_module("java_code_reviewer.nodes.reviewer_node")


def test_parse_issues_handles_brackets_inside_strings():
    response = """```json
[
  {
    "severity": "warning",
    "rule_id": "TEST-001",
    "file_path": "src/Example.java",
    "line_number": 7,
    "message": "Avoid array text like [x] in logs",
    "code_snippet": "log.info(\\"value [x]\\");"
  }
]
```"""

    issues = _parse_issues(response)

    assert len(issues) == 1
    assert issues[0]["severity"] == Severity.WARNING
    assert issues[0]["message"] == "Avoid array text like [x] in logs"


def test_parse_feedback_handles_nested_arrays():
    response = """```json
{
  "approved": false,
  "summary": "Needs changes",
  "missing_issues": ["one", "two"],
  "corrections_needed": ["fix rule"]
}
```"""

    approved, message = _parse_feedback_response(response)

    assert approved is False
    assert "Needs changes" in message
    assert "fix rule" in message


def test_parse_feedback_treats_string_false_as_false():
    response = """```json
{
  "approved": "false",
  "summary": "Needs another pass"
}
```"""

    approved, message = _parse_feedback_response(response)

    assert approved is False
    assert "Needs another pass" in message


def test_parse_patch_response_handles_braces_inside_content():
    response = """```json
{
  "src/Example.java": "class Example { void run() {} }"
}
```"""

    patch_files = _parse_patch_response(response)

    assert patch_files["src/Example.java"] == "class Example { void run() {} }"


def test_reviewer_node_marks_unparseable_llm_response_as_error():
    state = {
        "pr_url": "https://github.com/org/repo/pull/1",
        "mode": ReviewMode.AUDIT_ONLY,
        "validated": True,
        "provider": "github",
        "repo_owner": "org",
        "repo_name": "repo",
        "pr_number": 1,
        "diff_content": "+bad();",
        "changed_files": ["src/Example.java"],
        "pr_title": "Test PR",
        "pr_description": "",
        "retrieved_context": {},
        "issues": [],
        "route_decision": "report",
        "markdown_report": "",
    }

    with patch.object(reviewer_node_module, "LLMClient") as llm_cls:
        llm_cls.return_value.invoke.return_value = "I found no problems."

        result = reviewer_node_module.reviewer_node(state)

    assert result["issues"] == []
    assert "could not parse JSON issues" in result["error"]
