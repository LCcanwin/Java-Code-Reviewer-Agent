"""Unit tests for patch_node."""

import importlib
from unittest.mock import patch

from java_code_reviewer.state.review_state import ReviewMode, ReviewState, Severity

patch_node_module = importlib.import_module("java_code_reviewer.nodes.patch_node")


def _state() -> ReviewState:
    return {
        "pr_url": "https://github.com/org/repo/pull/1",
        "mode": ReviewMode.AUTOFIX,
        "validated": True,
        "provider": "github",
        "repo_owner": "org",
        "repo_name": "repo",
        "pr_number": 1,
        "base_branch": "main",
        "head_branch": "feature",
        "head_repo_owner": "org",
        "head_repo_name": "repo",
        "diff_content": "diff content",
        "changed_files": ["src/Example.java"],
        "pr_title": "Test PR",
        "pr_description": "",
        "retrieved_context": {},
        "issues": [
            {
                "severity": Severity.WARNING,
                "rule_id": "TEST-001",
                "file_path": "src/Example.java",
                "line_number": 1,
                "message": "Fix it",
                "code_snippet": "bad();",
            }
        ],
        "route_decision": "patch",
        "markdown_report": "",
    }


def test_json_default_serializes_enum_values():
    assert patch_node_module._json_default(Severity.WARNING) == "warning"


def test_patch_node_reads_original_files_and_filters_unknown_paths():
    state = _state()

    with patch.object(patch_node_module, "GitManager") as manager_cls:
        manager = manager_cls.return_value
        manager.read_files.return_value = {"src/Example.java": "class Example {}"}
        manager.branch_prefix = "java-reviewer/"
        manager.create_commit.return_value = "abc123"

        with patch.object(patch_node_module, "LLMClient") as llm_cls:
            llm = llm_cls.return_value
            llm.invoke.return_value = """```json
{
  "src/Example.java": "class Example { void fixed() {} }",
  "src/Other.java": "class Other {}"
}
```"""

            result = patch_node_module.patch_node(state)

    manager.read_files.assert_called_once_with(
        repo_owner="org",
        repo_name="repo",
        file_paths=["src/Example.java"],
        provider="github",
        branch="feature",
    )
    assert result["patch_files"] == {"src/Example.java": "class Example { void fixed() {} }"}
    assert result["patch_commit_sha"] == "abc123"
