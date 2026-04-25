"""Report node - generate Markdown table output."""

from ..state.review_state import ReviewState, Severity


SEVERITY_EMOJI = {
    Severity.BLOCKER: "[BLOCKER]",
    Severity.CRITICAL: "[CRITICAL]",
    Severity.WARNING: "[WARNING]",
    Severity.INFO: "[INFO]",
}

SEVERITY_ORDER = [Severity.BLOCKER, Severity.CRITICAL, Severity.WARNING, Severity.INFO]


def report_node(state: ReviewState) -> ReviewState:
    """Generate Markdown report from review issues."""
    issues = state.get("issues", [])

    if state.get("error") and not issues:
        state["markdown_report"] = (
            "# Java Code Review Report\n\n"
            f"Review failed: {state['error']}"
        )
        return state

    if not issues:
        state["markdown_report"] = "# Java Code Review Report\n\nNo issues found."
        return state

    sorted_issues = sorted(issues, key=lambda i: SEVERITY_ORDER.index(i["severity"]))

    lines = [
        "# Java Code Review Report",
        f"\n**PR**: {state.get('pr_title', 'N/A')}",
        f"**URL**: {state.get('pr_url', 'N/A')}",
        f"**Files Changed**: {len(state.get('changed_files', []))}",
        f"**Total Issues**: {len(issues)}",
        "\n## Issues Summary\n",
        "| Severity | Rule ID | File | Line | Message |",
        "|----------|---------|------|------|---------|",
    ]

    for issue in sorted_issues:
        emoji = SEVERITY_EMOJI.get(issue["severity"], "[?]")
        rule_id = issue["rule_id"]
        filepath = issue["file_path"]
        line = issue["line_number"]
        message = issue["message"].replace("|", "\\|").replace("\n", " ")[:100]

        lines.append(f"| {emoji} | {rule_id} | `{filepath}` | {line} | {message} |")

    lines.append("\n## Detailed Issues\n")

    for issue in sorted_issues:
        emoji = SEVERITY_EMOJI.get(issue["severity"], "[?]")
        lines.append(f"### {emoji} {issue['rule_id']}: {issue['file_path']}:{issue['line_number']}\n")
        lines.append(f"**Message**: {issue['message']}\n")
        lines.append(f"**Code**:\n```java\n{issue['code_snippet']}\n```\n")

        if suggestion := issue.get("suggestion"):
            lines.append(f"**Suggestion**:\n```java\n{suggestion}\n```\n")

        lines.append("---\n")

    state["markdown_report"] = "\n".join(lines)
    return state
