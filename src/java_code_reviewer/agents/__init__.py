"""PR agent abstractions for GitHub/GitLab."""

from .base import PRAgent
from .github_agent import GitHubAgent
from .gitlab_agent import GitLabAgent

__all__ = ["PRAgent", "GitHubAgent", "GitLabAgent"]
