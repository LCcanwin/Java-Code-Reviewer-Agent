"""Crawler node - fetch PR metadata and diff."""

from ..agents.github_agent import GitHubAgent
from ..agents.gitlab_agent import GitLabAgent
from ..state.review_state import ReviewState


def crawler_node(state: ReviewState) -> ReviewState:
    """Fetch PR metadata and diff content."""
    provider = state["provider"]
    owner = state["repo_owner"]
    repo = state["repo_name"]
    pr_number = state["pr_number"]

    try:
        if provider == "github":
            agent = GitHubAgent()
        elif provider == "gitlab":
            agent = GitLabAgent()
        else:
            state["error"] = f"Unknown provider: {provider}"
            return state

        metadata = agent.fetch_pr_metadata(owner, repo, pr_number)

        state["diff_content"] = metadata.diff_content
        state["changed_files"] = metadata.changed_files
        state["pr_title"] = metadata.title
        state["pr_description"] = metadata.description

    except Exception as e:
        state["error"] = f"Failed to fetch PR: {str(e)}"

    return state
