"""Reviewer node - LLM review against Alibaba standards."""

import json

from ..llm.client import LLMClient
from ..llm.prompts import REVIEW_PROMPT, SYSTEM_PROMPT
from ..state.review_state import Issue, ReviewState, Severity


def reviewer_node(state: ReviewState) -> ReviewState:
    """Perform LLM-based code review against Alibaba standards."""
    diff_content = state.get("diff_content", "")
    changed_files = state.get("changed_files", [])
    pr_title = state.get("pr_title", "")
    retrieved_context = state.get("retrieved_context", {})
    repair_prompt = state.get("repair_prompt", "")

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
                retrieved_context=(context_str or "No specific context retrieved.")
                + (f"\n\n## 恢复重试附加要求\n{repair_prompt}" if repair_prompt else ""),
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
    import logging

    logger = logging.getLogger(__name__)
    issues: list[Issue] = []

    json_text = _extract_json_array(response)
    if not json_text:
        logger.warning("No JSON array found in LLM response, returning empty issues")
        return issues

    try:
        parsed = json.loads(json_text)
        if not isinstance(parsed, list):
            logger.warning("Parsed JSON is not a list, returning empty issues")
            return issues

        for idx, item in enumerate(parsed):
            if not isinstance(item, dict):
                logger.warning(f"Item {idx} is not a dict, skipping: {item}")
                continue

            severity_str = item.get("severity", "warning")
            try:
                severity = Severity(severity_str)
            except ValueError:
                severity = Severity.WARNING

            line_number = 0
            try:
                line_number = int(item.get("line_number", 0))
            except (ValueError, TypeError):
                logger.warning(f"Invalid line_number '{item.get('line_number')}' for item {idx}, defaulting to 0")

            issue: Issue = {
                "severity": severity,
                "rule_id": item.get("rule_id", "UNKNOWN"),
                "file_path": item.get("file_path", ""),
                "line_number": line_number,
                "message": item.get("message", ""),
                "code_snippet": item.get("code_snippet", ""),
            }

            if suggestion := item.get("suggestion"):
                issue["suggestion"] = suggestion

            issues.append(issue)

    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"JSON parsing failed: {e}, returning empty issues")

    return issues


def _extract_json_array(response: str) -> str:
    """Extract the first complete JSON array from an LLM response."""
    import re

    fenced_match = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", response)
    if fenced_match:
        return fenced_match.group(1)

    start = response.find("[")
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
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return response[start : idx + 1]

    return ""
