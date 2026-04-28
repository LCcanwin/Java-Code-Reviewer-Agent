"""GitHub PR agent using PyGithub."""

import urllib.request
import logging
from typing import Optional

from github import Github
from github.GithubException import GithubException

from ..config import get_config
from .base import PRAgent, PRMetadata

logger = logging.getLogger(__name__)


class GitHubAgent(PRAgent):
    """GitHub PR operations via PyGithub."""

    def __init__(self, token: Optional[str] = None):
        cfg = get_config()
        self._token = token or cfg.github_token
        self._client = Github(self._token) if self._token else Github()

    def fetch_pr_metadata(self, repo_owner: str, repo_name: str, pr_number: int) -> PRMetadata:
        """Fetch PR metadata from GitHub."""
        repo = self._client.get_repo(f"{repo_owner}/{repo_name}")
        pr = repo.get_pull(pr_number)

        diff_content = self._fetch_diff(pr.raw_data.get("diff_url"))
        changed_files = [f.filename for f in pr.get_files()]

        return PRMetadata(
            repo_owner=repo_owner,
            repo_name=repo_name,
            pr_number=pr_number,
            title=pr.title,
            description=pr.body or "",
            diff_content=diff_content,
            changed_files=changed_files,
            base_branch=pr.base.ref,
            head_branch=pr.head.ref,
            head_repo_owner=pr.head.repo.owner.login if pr.head.repo else repo_owner,
            head_repo_name=pr.head.repo.name if pr.head.repo else repo_name,
        )

    def validate_token(self) -> bool:
        """Check token has required scopes."""
        try:
            self._client.get_user().login
            return True
        except GithubException:
            return False

    def _fetch_diff(self, diff_url: str) -> str:
        """Fetch diff content from URL with retry."""
        import time

        for attempt in range(3):
            try:
                headers = {}
                if self._token:
                    headers["Authorization"] = f"token {self._token}"
                req = urllib.request.Request(diff_url, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as response:
                    return response.read().decode("utf-8")
            except Exception as e:
                logger.warning(f"Failed to fetch diff (attempt {attempt + 1}/3): {e}")
                if attempt < 2:
                    time.sleep(1)
        return ""
