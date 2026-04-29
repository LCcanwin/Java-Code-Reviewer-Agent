"""Unit tests for context providers and merging."""

from unittest.mock import patch

from java_code_reviewer.context.merger import ContextMerger
from java_code_reviewer.context.repo_index_mcp import RepoIndexMCPProvider
from java_code_reviewer.nodes.context_retriever import context_retriever_node
from java_code_reviewer.state.review_state import ReviewMode, ReviewState


def _state() -> ReviewState:
    return {
        "pr_url": "https://github.com/org/repo/pull/1",
        "mode": ReviewMode.AUDIT_ONLY,
        "validated": True,
        "provider": "github",
        "repo_owner": "org",
        "repo_name": "repo",
        "pr_number": 1,
        "base_branch": "main",
        "head_branch": "feature",
        "diff_content": "diff --git a/src/Example.java b/src/Example.java\n+public class Example {}",
        "changed_files": ["src/Example.java"],
        "pr_title": "Test PR",
        "pr_description": "",
        "retrieved_context": {},
        "issues": [],
        "route_decision": "report",
        "markdown_report": "",
    }


def test_context_merger_preserves_provider_order_and_truncates():
    merger = ContextMerger(max_chars_per_file=80)

    merged = merger.merge(
        [
            ("rules", {"src/A.java": "A" * 40}),
            ("repo", {"src/A.java": "B" * 80}),
        ]
    )

    assert "### Source: rules" in merged["src/A.java"]
    assert "[Context truncated]" in merged["src/A.java"]
    assert len(merged["src/A.java"]) <= 80


def test_context_retriever_merges_enabled_provider_context():
    state = _state()

    with patch("java_code_reviewer.nodes.context_retriever._build_providers") as build_providers:
        provider = type(
            "FakeProvider",
            (),
            {
                "name": "fake",
                "retrieve": lambda self, state: {"src/Example.java": "fake context"},
            },
        )()
        build_providers.return_value = [provider]

        result = context_retriever_node(state)

    assert result["context_sources"] == ["fake"]
    assert "fake context" in result["retrieved_context"]["src/Example.java"]


def test_context_retriever_records_provider_errors_and_continues():
    state = _state()

    class FailingProvider:
        name = "repo_index_mcp"

        def retrieve(self, state):
            raise RuntimeError("token=secret")

    with patch("java_code_reviewer.nodes.context_retriever._build_providers", return_value=[FailingProvider()]):
        result = context_retriever_node(state)

    assert result["retrieved_context"] == {}
    assert result["context_errors"][0]["recoverable"] is True
    assert "secret" not in result["context_errors"][0]["message"]
    assert "***REDACTED***" in result["context_errors"][0]["message"]


def test_repo_index_mcp_provider_uses_injected_client():
    state = _state()

    class FakeClient:
        def search_repository_context(self, **kwargs):
            assert kwargs["repo_owner"] == "org"
            assert kwargs["branch"] == "feature"
            return {"Definitions": "class Example {}"}

    with patch("java_code_reviewer.context.repo_index_mcp.get_config") as get_config:
        cfg = get_config.return_value
        cfg.repo_index_mcp_enabled = True
        cfg.repo_index_mcp_max_files = 10
        cfg.repo_index_mcp_max_snippets_per_file = 3
        cfg.repo_index_mcp_include_tests = True
        cfg.repo_index_mcp_include_references = True
        cfg.repo_index_mcp_include_related_files = True

        result = RepoIndexMCPProvider(client=FakeClient()).retrieve(state)

    assert "Definitions" in result["src/Example.java"]
    assert "class Example" in result["src/Example.java"]
