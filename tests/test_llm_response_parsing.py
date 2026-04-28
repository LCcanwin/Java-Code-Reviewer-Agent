"""Unit tests for LLM response parsing helpers."""

from java_code_reviewer.nodes.feedback_node import _parse_feedback_response
from java_code_reviewer.nodes.patch_node import _parse_patch_response
from java_code_reviewer.nodes.reviewer_node import _parse_issues
from java_code_reviewer.state.review_state import Severity


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


def test_parse_patch_response_handles_braces_inside_content():
    response = """```json
{
  "src/Example.java": "class Example { void run() {} }"
}
```"""

    patch_files = _parse_patch_response(response)

    assert patch_files["src/Example.java"] == "class Example { void run() {} }"
