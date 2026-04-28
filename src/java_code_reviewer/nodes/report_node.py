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

    if state.get("validation_error") and not issues:
        state["markdown_report"] = (
            "# Java Code Review Report\n\n"
            f"Validation failed: {state['validation_error']}"
        )
        return state

    if state.get("error") and not issues:
        state["markdown_report"] = (
            "# Java Code Review Report\n\n"
            f"Review failed: {state['error']}"
        )
        return state

    if state.get("patch_error") and not issues:
        state["markdown_report"] = (
            "# Java Code Review Report\n\n"
            f"Autofix failed: {state['patch_error']}"
        )
        return state

    if not issues:
        state["markdown_report"] = "# Java Code Review Report\n\nNo issues found."
        return state

    sorted_issues = sorted(issues, key=lambda i: _severity_rank(i["severity"]))

    lines = [
        "# Java Code Review Report",
        f"\n**PR**: {_escape_inline_markdown(str(state.get('pr_title', 'N/A')))}",
        f"**URL**: {_escape_inline_markdown(str(state.get('pr_url', 'N/A')))}",
        f"**Files Changed**: {len(state.get('changed_files', []))}",
        f"**Total Issues**: {len(issues)}",
        "\n## Issues Summary\n",
        "| Severity | Rule ID | File | Line | Message |",
        "|----------|---------|------|------|---------|",
    ]

    for issue in sorted_issues:
        emoji = SEVERITY_EMOJI.get(issue["severity"], "[?]")
        rule_id = _escape_table_cell(str(issue["rule_id"]))
        filepath = _escape_table_cell(str(issue["file_path"]))
        line = issue["line_number"]
        message = _escape_table_cell(str(issue["message"]))[:100]

        lines.append(f"| {emoji} | {rule_id} | `{filepath}` | {line} | {message} |")

    lines.append("\n## Detailed Issues\n")

    for issue in sorted_issues:
        emoji = SEVERITY_EMOJI.get(issue["severity"], "[?]")
        rule_id = _escape_inline_markdown(str(issue["rule_id"]))
        filepath = _escape_inline_markdown(str(issue["file_path"]))
        message = _escape_inline_markdown(str(issue["message"]))
        code_snippet = _escape_code_fence(str(issue["code_snippet"]))
        lines.append(f"### {emoji} {rule_id}: {filepath}:{issue['line_number']}\n")
        lines.append(f"**Message**: {message}\n")
        lines.append(f"**Code**:\n````java\n{code_snippet}\n````\n")

        if suggestion := issue.get("suggestion"):
            lines.append(f"**Suggestion**:\n````java\n{_escape_code_fence(str(suggestion))}\n````\n")

        lines.append("---\n")

    if state.get("patch_error"):
        lines.append("\n## Autofix Status\n")
        lines.append(f"Autofix failed: {_escape_inline_markdown(str(state['patch_error']))}\n")

    if state.get("recovery_actions"):
        lines.append("\n## Recovery Actions\n")
        for action in state["recovery_actions"]:
            lines.append(
                f"- `{_escape_inline_markdown(str(action.get('node', 'unknown')))}`: "
                f"{_escape_inline_markdown(str(action.get('action', 'unknown')))} - "
                f"{_escape_inline_markdown(str(action.get('reason', '')))}"
            )

    state["markdown_report"] = "\n".join(lines)
    return state


def _severity_rank(severity: Severity) -> int:
    try:
        return SEVERITY_ORDER.index(severity)
    except ValueError:
        return len(SEVERITY_ORDER)


def _escape_table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def _escape_inline_markdown(value: str) -> str:
    return value.replace("\n", " ").replace("\r", " ")


def _escape_code_fence(value: str) -> str:
    return value.replace("````", "` ` ` `")
