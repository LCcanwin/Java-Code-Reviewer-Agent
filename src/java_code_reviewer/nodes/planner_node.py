"""Planner node - creates a review plan based on diff and context."""

import json

from ..llm.client import LLMClient
from ..llm.prompts import PLANNER_SYSTEM_PROMPT, PLANNER_USER_PROMPT
from ..state.review_state import ReviewState


def planner_node(state: ReviewState) -> ReviewState:
    """Create a review plan based on the diff and retrieved context."""
    diff_content = state.get("diff_content", "")
    changed_files = state.get("changed_files", [])
    pr_title = state.get("pr_title", "")
    retrieved_context = state.get("retrieved_context", {})
    mode = state.get("mode", "audit_only")

    if not diff_content:
        state["planning_result"] = "No diff content to plan review."
        return state

    context_str = _format_context(retrieved_context)

    messages = [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": PLANNER_USER_PROMPT.format(
                pr_title=pr_title,
                changed_files=", ".join(changed_files[:20]),
                diff_content=diff_content[:15000],
                retrieved_context=context_str or "No specific context retrieved.",
                mode=mode.value if hasattr(mode, "value") else mode,
            ),
        },
    ]

    try:
        llm = LLMClient()
        response = llm.invoke(messages)

        planning_result = _parse_planning_response(response)
        state["planning_result"] = planning_result

    except Exception as e:
        state["error"] = f"Planning failed: {str(e)}"
        state["planning_result"] = ""

    return state


def _format_context(context: dict[str, str]) -> str:
    """Format retrieved context for prompt."""
    if not context:
        return ""
    parts = []
    for filepath, ctx in context.items():
        parts.append(f"### {filepath}\n{ctx}")
    return "\n\n".join(parts)


def _parse_planning_response(response: str) -> str:
    """Parse LLM planning response - return as formatted string."""
    import re

    json_match = re.search(r"\{[\s\S]*\}", response)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            if isinstance(parsed, dict):
                summary = parsed.get("plan_summary", "")
                focus_areas = parsed.get("focus_areas", [])
                priority_rules = parsed.get("priority_rules", [])

                result_parts = [f"Summary: {summary}"] if summary else []
                if focus_areas:
                    result_parts.append(f"Focus Areas: {', '.join(focus_areas)}")
                if priority_rules:
                    result_parts.append(f"Priority Rules: {', '.join(priority_rules)}")

                return "\n".join(result_parts) if result_parts else response
        except json.JSONDecodeError:
            pass

    return response
