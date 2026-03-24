"""Patch node - generate and push fixes to PR."""

import json
from typing import Any

from ..git_ops.git_manager import GitManager
from ..llm.client import LLMClient
from ..llm.prompts import PATCH_PROMPT, SYSTEM_PROMPT
from ..state.review_state import ReviewState


def patch_node(state: ReviewState) -> ReviewState:
    """Generate fixes and push to PR in AUTOFIX mode."""
    diff_content = state.get("diff_content", "")
    pr_title = state.get("pr_title", "")
    issues = state.get("issues", [])

    if not issues:
        state["patch_files"] = {}
        return state

    issues_text = json.dumps(issues, indent=2, ensure_ascii=False)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": PATCH_PROMPT.format(
                pr_title=pr_title,
                diff_content=diff_content[:15000],
                issues=issues_text,
            ),
        },
    ]

    try:
        llm = LLMClient()
        response = llm.invoke(messages)

        patch_files = _parse_patch_response(response)
        state["patch_files"] = patch_files

        if patch_files:
            commit_sha = _push_patches(state, patch_files)
            state["patch_commit_sha"] = commit_sha

    except Exception as e:
        state["patch_error"] = f"Patch generation failed: {str(e)}"
        state["patch_files"] = {}

    return state


def _parse_patch_response(response: str) -> dict[str, str]:
    """Parse LLM response into patch files dict."""
    import re

    patch_files: dict[str, str] = {}

    json_match = re.search(r"\{[\s\S]*\}", response)
    if not json_match:
        return patch_files

    try:
        parsed = json.loads(json_match.group())
        if isinstance(parsed, dict):
            for filepath, content in parsed.items():
                if isinstance(filepath, str) and isinstance(content, str):
                    patch_files[filepath] = content
    except json.JSONDecodeError:
        pass

    return patch_files


def _push_patches(state: ReviewState, patch_files: dict[str, str]) -> str:
    """Push patches to PR via GitManager."""
    git_manager = GitManager()

    branch_name = f"{git_manager.branch_prefix}autofix/{state['pr_number']}"

    try:
        commit_sha = git_manager.create_commit(
            repo_owner=state["repo_owner"],
            repo_name=state["repo_name"],
            branch_name=branch_name,
            patch_files=patch_files,
            message=f"fix: Apply Alibaba standards fixes",
        )
        return commit_sha
    except Exception as e:
        state["patch_error"] = f"Failed to push patches: {str(e)}"
        return ""
