"""Feedback node - validates review issues against the review plan."""

import json

from ..llm.client import LLMClient
from ..llm.prompts import FEEDBACK_SYSTEM_PROMPT, FEEDBACK_USER_PROMPT
from ..state.review_state import Issue, ReviewState


def feedback_node(state: ReviewState) -> ReviewState:
    """Validate review issues against the planning and standards."""
    issues = state.get("issues", [])
    planning_result = state.get("planning_result", "")
    retrieved_context = state.get("retrieved_context", {})
    diff_content = state.get("diff_content", "")

    feedback_iteration = state.get("feedback_iteration", 0)
    state["feedback_iteration"] = feedback_iteration + 1

    if not issues and not planning_result:
        state["feedback_approved"] = True
        state["feedback_message"] = "No issues to review and no planning result."
        return state

    context_str = _format_context(retrieved_context)
    issues_str = _format_issues(issues)

    messages = [
        {"role": "system", "content": FEEDBACK_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": FEEDBACK_USER_PROMPT.format(
                planning_result=planning_result or "No specific plan.",
                issues=issues_str or "No issues found.",
                retrieved_context=context_str or "No specific context retrieved.",
                diff_content=diff_content[:5000],
            ),
        },
    ]

    try:
        llm = LLMClient()
        response = llm.invoke(messages)

        approved, message = _parse_feedback_response(response)
        state["feedback_approved"] = approved
        state["feedback_message"] = message

    except Exception as e:
        state["error"] = f"Feedback check failed: {str(e)}"
        state["feedback_approved"] = False
        state["feedback_message"] = f"Feedback check error: {str(e)}"

    return state


def _format_context(context: dict[str, str]) -> str:
    """Format retrieved context for prompt."""
    if not context:
        return ""
    parts = []
    for filepath, ctx in context.items():
        parts.append(f"### {filepath}\n{ctx}")
    return "\n\n".join(parts)


def _format_issues(issues: list[Issue]) -> str:
    """Format issues list for prompt."""
    if not issues:
        return "No issues found."

    parts = []
    for i, issue in enumerate(issues, 1):
        severity = issue.get("severity", "unknown")
        severity_val = severity.value if hasattr(severity, "value") else severity
        parts.append(
            f"{i}. [{severity_val.upper()}] {issue.get('rule_id', 'UNKNOWN')} - "
            f"{issue.get('file_path', 'unknown')}:{issue.get('line_number', 0)}\n"
            f"   Message: {issue.get('message', '')}\n"
            f"   Code: {issue.get('code_snippet', '')}"
        )
    return "\n".join(parts)


def _parse_feedback_response(response: str) -> tuple[bool, str]:
    """Parse LLM feedback response into approved flag and message."""
    import re

    json_match = re.search(r"\{[\s\S]*?\}", response)
    if not json_match:
        return False, "Could not parse feedback response"

    try:
        parsed = json.loads(json_match.group())
        if not isinstance(parsed, dict):
            return False, "Parsed response is not a valid dictionary"

        approved = parsed.get("approved", False)
        summary = parsed.get("summary", "")

        corrections = parsed.get("corrections_needed", [])
        corrections_str = ""
        if corrections:
            corrections_str = "\nCorrections needed: " + "; ".join(corrections)

        missing = parsed.get("missing_issues", [])
        missing_str = ""
        if missing:
            missing_str = "\nMissing issues: " + "; ".join(missing)

        message = f"{summary}{corrections_str}{missing_str}"

        return bool(approved), message if message else response

    except json.JSONDecodeError:
        return False, "Could not parse feedback JSON"
