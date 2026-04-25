"""Option router - route to Report or Patch node based on mode."""

from ..state.review_state import ReviewMode, ReviewState


def option_router_node(state: ReviewState) -> ReviewState:
    """Route to report or patch node based on review mode."""
    if state.get("error"):
        state["route_decision"] = "report"
        return state

    mode = state["mode"]

    if mode == ReviewMode.AUTOFIX:
        state["route_decision"] = "patch"
    else:
        state["route_decision"] = "report"

    return state
