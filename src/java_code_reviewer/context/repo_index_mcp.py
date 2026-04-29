"""Optional repository index MCP context provider.

This provider is intentionally a thin adapter shell. It defines the query shape
and fallback behavior without introducing a hard MCP SDK dependency into the
core review pipeline.
"""

from typing import Optional

from ..config import get_config
from ..state.review_state import ReviewState


class RepoIndexMCPProvider:
    """Retrieve repository code context from a future MCP code-search server."""

    name = "repo_index_mcp"

    def __init__(self, client: Optional[object] = None):
        self._client = client

    def retrieve(self, state: ReviewState) -> dict[str, str]:
        cfg = get_config()
        if not cfg.repo_index_mcp_enabled:
            return {}

        if self._client is None:
            raise RuntimeError("Repo index MCP provider is enabled but no MCP client is configured")

        changed_files = state.get("changed_files", [])[: cfg.repo_index_mcp_max_files]
        if not changed_files:
            return {}

        # The actual MCP client is injected later. The expected adapter contract
        # is intentionally small: search related repository context per file.
        context: dict[str, str] = {}
        for filepath in changed_files:
            result = self._client.search_repository_context(
                repo_owner=state["repo_owner"],
                repo_name=state["repo_name"],
                branch=state.get("head_branch") or state.get("base_branch") or "",
                filepath=filepath,
                diff_content=state.get("diff_content", ""),
                max_snippets=cfg.repo_index_mcp_max_snippets_per_file,
                include_tests=cfg.repo_index_mcp_include_tests,
                include_references=cfg.repo_index_mcp_include_references,
                include_related_files=cfg.repo_index_mcp_include_related_files,
            )
            if result:
                context[filepath] = self._format_result(result)

        return context

    def _format_result(self, result: object) -> str:
        if isinstance(result, str):
            return f"## Repository Context\n\n{result}"
        if isinstance(result, dict):
            parts = ["## Repository Context"]
            for key, value in result.items():
                if value:
                    parts.append(f"### {key}\n{value}")
            return "\n\n".join(parts)
        return f"## Repository Context\n\n{result}"
