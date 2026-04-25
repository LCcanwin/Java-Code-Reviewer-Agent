"""Input node - URL validation and permission check."""

import re
from typing import Literal, Optional, Tuple

from ..config import get_config
from ..state.review_state import ReviewState


# Regex patterns for PR URLs
GITHUB_PATTERN = re.compile(
    r"https?://(?:www\.)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<pr>\d+)"
)
GITLAB_PATTERN = re.compile(
    r"https?://(?:www\.)?gitlab\.com/(?P<project>.+?)/-/merge_requests/(?P<pr>\d+)(?:[/?#].*)?$"
)


def parse_pr_url(pr_url: str) -> Tuple[Optional[Literal["github", "gitlab"]], str, str, int]:
    """Parse PR URL and return (provider, owner, repo, pr_number)."""
    if match := GITHUB_PATTERN.match(pr_url):
        return "github", match.group("owner"), match.group("repo"), int(match.group("pr"))
    if match := GITLAB_PATTERN.match(pr_url):
        project_path = match.group("project").strip("/")
        owner, _, repo = project_path.rpartition("/")
        if owner and repo:
            return "gitlab", owner, repo, int(match.group("pr"))
    return None, "", "", 0


def check_scope_limit(provider: str, owner: str, repo: str) -> bool:
    """Check if the repo is in the allowed scope whitelist."""
    cfg = get_config()
    allowed = cfg.scope_limit
    if not allowed:
        return True
    return f"{owner}/{repo}" in allowed


def input_node(state: ReviewState) -> ReviewState:
    """Validate PR URL and check permissions."""
    pr_url = state["pr_url"]
    provider, owner, repo, pr_number = parse_pr_url(pr_url)

    if provider is None:
        state["validated"] = False
        state["validation_error"] = "Invalid PR URL format. Expected GitHub or GitLab URL."
        return state

    if not check_scope_limit(provider, owner, repo):
        state["validated"] = False
        state["validation_error"] = f"Repository {owner}/{repo} is not in the allowed scope."
        return state

    state["validated"] = True
    state["provider"] = provider
    state["repo_owner"] = owner
    state["repo_name"] = repo
    state["pr_number"] = pr_number

    return state
