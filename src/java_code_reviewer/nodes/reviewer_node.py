"""Reviewer node - LLM review against Alibaba standards."""

import json
from typing import Any

from ..llm.client import LLMClient
from ..llm.prompts import REVIEW_PROMPT, SYSTEM_PROMPT
from ..state.review_state import Issue, ReviewState, Severity


def reviewer_node(state: ReviewState) -> ReviewState:
    """Perform LLM-based code review against Alibaba standards."""
    diff_content = state.get("diff_content", "")
    changed_files = state.get("changed_files", [])
    pr_title = state.get("pr_title", "")
    retrieved_context = state.get("retrieved_context", {})

    if not diff_content:
        state["issues"] = []
        return state

    context_str = _format_context(retrieved_context)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": REVIEW_PROMPT.format(
                pr_title=pr_title,
                changed_files=", ".join(changed_files[:20]),
                diff_content=diff_content[:15000],
                retrieved_context=context_str or "No specific context retrieved.",
            ),
        },
    ]

    try:
        llm = LLMClient()
        response = llm.invoke(messages)

        issues = _parse_issues(response)
        state["issues"] = issues

    except Exception as e:
        state["error"] = f"Review failed: {str(e)}"
        state["issues"] = []

    return state


def _format_context(context: dict[str, str]) -> str:
    """Format retrieved context for prompt."""
    if not context:
        return ""
    parts = []
    for filepath, ctx in context.items():
        parts.append(f"### {filepath}\n{ctx}")
    return "\n\n".join(parts)


def _parse_issues(response: str) -> list[Issue]:
    """Parse LLM response into Issue list."""
    import re

    issues: list[Issue] = []

    json_match = re.search(r"\[[\s\S]*\]", response)
    if not json_match:
        return issues

    try:
        parsed = json.loads(json_match.group())
        if not isinstance(parsed, list):
            return issues

        for item in parsed:
            if not isinstance(item, dict):
                continue

            severity_str = item.get("severity", "warning")
            try:
                severity = Severity(severity_str)
            except ValueError:
                severity = Severity.WARNING

            issue: Issue = {
                "severity": severity,
                "rule_id": item.get("rule_id", "UNKNOWN"),
                "file_path": item.get("file_path", ""),
                "line_number": int(item.get("line_number", 0)),
                "message": item.get("message", ""),
                "code_snippet": item.get("code_snippet", ""),
            }

            if suggestion := item.get("suggestion"):
                issue["suggestion"] = suggestion

            issues.append(issue)

    except (json.JSONDecodeError, ValueError):
        pass

    return issues
