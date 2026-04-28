"""Main entry point - LangGraph compilation and run_review function."""

from typing import Literal

from langgraph.graph import END, StateGraph

from .nodes import (
    crawler_node,
    context_retriever_node,
    input_node,
    option_router_node,
    patch_node,
    planner_node,
    report_node,
    reviewer_node,
    feedback_node,
    failure_handler_node,
)
from .observability import mark_run_finished, wrap_node
from .state.review_state import ErrorType, ReviewMode, ReviewState, RunStatus


MAX_FEEDBACK_ITERATIONS = 1


def _should_proceed_to_crawler(state: ReviewState) -> bool:
    """Check if we should proceed to crawler after input."""
    return bool(state.get("validated", False))


def _has_pending_recovery(state: ReviewState) -> bool:
    """Return whether the last node failure should be handled."""
    return bool(state.get("pending_recovery"))


def _should_proceed_to_retriever(state: ReviewState) -> bool:
    """Check if we should proceed to context retriever after crawler."""
    return "diff_content" in state and not state.get("error")


def _should_proceed_to_planner(state: ReviewState) -> bool:
    """Check if we should proceed to planner after context retriever."""
    # Skip planner in audit_only mode to save LLM call
    if state.get("mode") == ReviewMode.AUDIT_ONLY:
        return False
    return "retrieved_context" in state and not state.get("error")


def _should_proceed_to_reviewer(state: ReviewState) -> bool:
    """Check if we should proceed to reviewer after planner."""
    # In audit_only mode, skip planner and go directly to reviewer
    if state.get("mode") == ReviewMode.AUDIT_ONLY:
        return "diff_content" in state and not state.get("error")
    return "planning_result" in state and not state.get("error")


def _should_retry_review(state: ReviewState) -> bool:
    """Check if we should retry review (feedback not approved and under max iterations)."""
    return (
        not state.get("feedback_approved", False)
        and state.get("feedback_iteration", 0) < MAX_FEEDBACK_ITERATIONS
    )


def _should_proceed_to_router(state: ReviewState) -> bool:
    """Check if we should proceed to option router (feedback approved or audit_only mode)."""
    if state.get("mode") == ReviewMode.AUDIT_ONLY:
        return True  # Skip feedback loop in audit_only mode
    return state.get("feedback_approved", False)


def _route_after_feedback(state: ReviewState) -> str:
    if _has_pending_recovery(state):
        return "recover"
    if _should_retry_review(state):
        return "retry"
    if _should_proceed_to_router(state):
        return "router"
    state["failed_node"] = "feedback"
    state["failure_type"] = ErrorType.FEEDBACK_REJECTED.value
    state["failure_message"] = state.get("feedback_message", "Feedback rejected the review result")
    state["pending_recovery"] = True
    state.setdefault("errors", []).append(
        {
            "node": "feedback",
            "error_type": ErrorType.FEEDBACK_REJECTED.value,
            "message": state["failure_message"],
            "recoverable": True,
        }
    )
    return "recover"


def compile_graph() -> StateGraph:
    """Compile the LangGraph state machine."""
    graph = StateGraph(ReviewState)

    graph.add_node("input", wrap_node("input", input_node))
    graph.add_node("crawler", wrap_node("crawler", crawler_node))
    graph.add_node("context_retriever", wrap_node("context_retriever", context_retriever_node))
    graph.add_node("planner", wrap_node("planner", planner_node))
    graph.add_node("reviewer", wrap_node("reviewer", reviewer_node))
    graph.add_node("feedback", wrap_node("feedback", feedback_node))
    graph.add_node("failure_handler", failure_handler_node)
    graph.add_node("option_router", wrap_node("option_router", option_router_node))
    graph.add_node("report", wrap_node("report", report_node))
    graph.add_node("patch", wrap_node("patch", patch_node))

    graph.set_entry_point("input")

    graph.add_conditional_edges(
        "input",
        lambda state: "recover" if _has_pending_recovery(state) else "crawler" if _should_proceed_to_crawler(state) else "end",
        {
            "recover": "failure_handler",
            "crawler": "crawler",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "crawler",
        lambda state: "recover" if _has_pending_recovery(state) else "retriever" if _should_proceed_to_retriever(state) else "end",
        {
            "recover": "failure_handler",
            "retriever": "context_retriever",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "context_retriever",
        lambda state: (
            "recover"
            if _has_pending_recovery(state)
            else "planner"
            if _should_proceed_to_planner(state)
            else "reviewer"
        ),
        {
            "recover": "failure_handler",
            "planner": "planner",
            "reviewer": "reviewer",
        },
    )

    graph.add_conditional_edges(
        "planner",
        lambda state: "recover" if _has_pending_recovery(state) else "reviewer" if _should_proceed_to_reviewer(state) else "end",
        {
            "recover": "failure_handler",
            "reviewer": "reviewer",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "reviewer",
        lambda state: "recover" if _has_pending_recovery(state) else "feedback",
        {
            "recover": "failure_handler",
            "feedback": "feedback",
        },
    )

    graph.add_conditional_edges(
        "feedback",
        _route_after_feedback,
        {
            "recover": "failure_handler",
            "retry": "reviewer",
            "router": "option_router",
        },
    )

    graph.add_conditional_edges(
        "failure_handler",
        _route_after_recovery,
        {
            "crawler": "crawler",
            "context_retriever": "context_retriever",
            "planner": "planner",
            "reviewer": "reviewer",
            "feedback": "feedback",
            "patch": "patch",
            "option_router": "option_router",
            "report": "report",
            "end": END,
        },
    )

    graph.add_conditional_edges(
        "option_router",
        lambda state: state.get("route_decision", "report"),
        {
            "report": "report",
            "patch": "patch",
        },
    )

    graph.add_edge("report", END)
    graph.add_conditional_edges(
        "patch",
        lambda state: "recover" if _has_pending_recovery(state) else "end",
        {
            "recover": "failure_handler",
            "end": END,
        },
    )

    return graph.compile()


def _route_after_recovery(state: ReviewState) -> str:
    """Route according to the bounded recovery decision."""
    action = state.get("recovery_action", "")
    failed_node = state.get("failed_node", "")

    if action in {"retry", "retry_with_repair_prompt"}:
        return failed_node if failed_node in {"crawler", "planner", "reviewer", "feedback", "patch"} else "end"
    if action == "skip_node":
        return _next_node_after_skip(state, failed_node)
    if action in {"fallback_audit_only", "partial_success", "fail"}:
        return "report"
    return "end"


def _next_node_after_skip(state: ReviewState, failed_node: str) -> str:
    if failed_node == "context_retriever":
        return "reviewer" if state.get("mode") == ReviewMode.AUDIT_ONLY else "planner"
    if failed_node == "planner":
        return "reviewer"
    if failed_node == "feedback":
        return "option_router" if state.get("mode") == ReviewMode.AUDIT_ONLY else "report"
    return "report"


GRAPH = compile_graph()


def run_review(pr_url: str, mode: Literal["audit_only", "autofix"] = "audit_only") -> ReviewState:
    """Run the code review pipeline on a PR URL.

    Args:
        pr_url: GitHub or GitLab PR URL
        mode: "audit_only" for Markdown report, "autofix" for patch generation

    Returns:
        ReviewState with review results
    """
    initial_state: ReviewState = {
        "status": RunStatus.RUNNING,
        "node_results": {},
        "errors": [],
        "recovery_actions": [],
        "current_node": "",
        "pending_recovery": False,
        "recovery_action": "",
        "repair_prompt": "",
        "pr_url": pr_url,
        "mode": ReviewMode(mode),
        "validated": False,
        "provider": "github",
        "repo_owner": "",
        "repo_name": "",
        "pr_number": 0,
        "base_branch": "",
        "head_branch": "",
        "head_repo_owner": "",
        "head_repo_name": "",
        "diff_content": "",
        "changed_files": [],
        "pr_title": "",
        "pr_description": "",
        "retrieved_context": {},
        "issues": [],
        "route_decision": "report",
        "markdown_report": "",
        "feedback_iteration": 0,
        "feedback_approved": False,
        "planning_result": "" if mode == "audit_only" else None,
    }

    result = GRAPH.invoke(initial_state)
    return mark_run_finished(result)
