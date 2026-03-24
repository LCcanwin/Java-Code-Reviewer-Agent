"""Main entry point - LangGraph compilation and run_review function."""

from typing import Literal

from langgraph.graph import END, StateGraph

from .nodes import (
    crawler_node,
    context_retriever_node,
    input_node,
    option_router_node,
    patch_node,
    report_node,
    reviewer_node,
)
from .state.review_state import ReviewMode, ReviewState


def _should_proceed_to_crawler(state: ReviewState) -> bool:
    """Check if we should proceed to crawler after input."""
    return bool(state.get("validated", False))


def _should_proceed_to_retriever(state: ReviewState) -> bool:
    """Check if we should proceed to context retriever after crawler."""
    return "diff_content" in state and not state.get("error")


def _should_proceed_to_reviewer(state: ReviewState) -> bool:
    """Check if we should proceed to reviewer after context retriever."""
    return "retrieved_context" in state and not state.get("error")


def compile_graph() -> StateGraph:
    """Compile the LangGraph state machine."""
    graph = StateGraph(ReviewState)

    graph.add_node("input", input_node)
    graph.add_node("crawler", crawler_node)
    graph.add_node("context_retriever", context_retriever_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("option_router", option_router_node)
    graph.add_node("report", report_node)
    graph.add_node("patch", patch_node)

    graph.set_entry_point("input")

    graph.add_conditional_edges(
        "input",
        _should_proceed_to_crawler,
        {
            True: "crawler",
            False: END,
        },
    )

    graph.add_conditional_edges(
        "crawler",
        _should_proceed_to_retriever,
        {
            True: "context_retriever",
            False: END,
        },
    )

    graph.add_conditional_edges(
        "context_retriever",
        _should_proceed_to_reviewer,
        {
            True: "reviewer",
            False: END,
        },
    )

    graph.add_edge("reviewer", "option_router")

    graph.add_conditional_edges(
        "option_router",
        lambda state: state.get("route_decision", "report"),
        {
            "report": "report",
            "patch": "patch",
        },
    )

    graph.add_edge("report", END)
    graph.add_edge("patch", END)

    return graph.compile()


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
        "pr_url": pr_url,
        "mode": ReviewMode(mode),
        "validated": False,
        "provider": "github",
        "repo_owner": "",
        "repo_name": "",
        "pr_number": 0,
        "diff_content": "",
        "changed_files": [],
        "pr_title": "",
        "pr_description": "",
        "retrieved_context": {},
        "issues": [],
        "route_decision": "report",
        "markdown_report": "",
    }

    result = GRAPH.invoke(initial_state)
    return result
