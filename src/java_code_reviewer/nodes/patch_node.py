"""Patch node - generate and push fixes to PR."""

import json

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

    try:
        git_manager = GitManager()
        file_paths = _issue_file_paths(state)
        original_files = git_manager.read_files(
            repo_owner=state.get("head_repo_owner") or state["repo_owner"],
            repo_name=state.get("head_repo_name") or state["repo_name"],
            file_paths=file_paths,
            provider=state["provider"],
            branch=state.get("head_branch") or None,
        )
    except Exception as e:
        state["patch_error"] = f"Patch generation failed: could not read PR files: {str(e)}"
        state["patch_files"] = {}
        return state

    if file_paths and not original_files:
        state["patch_error"] = "Patch generation failed: no changed files could be read from the PR head branch"
        state["patch_files"] = {}
        return state

    issues_text = json.dumps(issues, indent=2, ensure_ascii=False, default=_json_default)
    original_files_text = json.dumps(original_files, indent=2, ensure_ascii=False)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": PATCH_PROMPT.format(
                pr_title=pr_title,
                diff_content=diff_content[:15000],
                issues=issues_text,
                original_files=original_files_text,
            ),
        },
    ]

    try:
        llm = LLMClient()
        response = llm.invoke(messages)

        patch_files = _parse_patch_response(response)
        patch_files = {
            filepath: content
            for filepath, content in patch_files.items()
            if filepath in original_files
        }
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
    patch_files: dict[str, str] = {}

    json_text = _extract_json_object(response)
    if not json_text:
        return patch_files

    try:
        parsed = json.loads(json_text)
        if isinstance(parsed, dict):
            for filepath, content in parsed.items():
                if isinstance(filepath, str) and isinstance(content, str):
                    patch_files[filepath] = content
    except json.JSONDecodeError:
        pass

    return patch_files


def _extract_json_object(response: str) -> str:
    """Extract the first complete JSON object from an LLM response."""
    import re

    fenced_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", response)
    if fenced_match:
        return fenced_match.group(1)

    start = response.find("{")
    if start == -1:
        return ""

    in_string = False
    escape = False
    depth = 0
    for idx in range(start, len(response)):
        char = response[idx]
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return response[start : idx + 1]

    return ""


def _push_patches(state: ReviewState, patch_files: dict[str, str]) -> str:
    """Push patches to PR via GitManager."""
    git_manager = GitManager()

    branch_name = f"{git_manager.branch_prefix}autofix/{state['pr_number']}"

    try:
        commit_sha = git_manager.create_commit(
            repo_owner=state.get("head_repo_owner") or state["repo_owner"],
            repo_name=state.get("head_repo_name") or state["repo_name"],
            branch_name=branch_name,
            patch_files=patch_files,
            message=f"fix: Apply Alibaba standards fixes",
            provider=state["provider"],
            source_branch=state.get("head_branch") or None,
        )
        return commit_sha
    except Exception as e:
        state["patch_error"] = f"Failed to push patches: {str(e)}"
        return ""


def _issue_file_paths(state: ReviewState) -> list[str]:
    """Return changed files that have review issues."""
    changed_files = set(state.get("changed_files", []))
    file_paths = []
    for issue in state.get("issues", []):
        filepath = issue.get("file_path", "")
        if filepath and (not changed_files or filepath in changed_files):
            file_paths.append(filepath)
    return sorted(set(file_paths))


def _json_default(value: object) -> object:
    if hasattr(value, "value"):
        return value.value
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
