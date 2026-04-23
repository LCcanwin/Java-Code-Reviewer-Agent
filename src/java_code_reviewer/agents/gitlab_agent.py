"""GitLab PR agent using python-gitlab."""

from typing import Optional

import gitlab

from ..config import get_config
from .base import PRAgent, PRMetadata


class GitLabAgent(PRAgent):
    """GitLab MR operations via python-gitlab."""

    def __init__(self, token: Optional[str] = None, api_url: Optional[str] = None):
        cfg = get_config()
        self._token = token or cfg.gitlab_token
        self._api_url = api_url or cfg.gitlab_api_url
        self._client = gitlab.Gitlab(self._api_url, private_token=self._token)

    def fetch_pr_metadata(self, repo_owner: str, repo_name: str, pr_number: int) -> PRMetadata:
        """Fetch MR metadata from GitLab."""
        project = self._client.projects.get(f"{repo_owner}/{repo_name}")
        mr = project.mergerequests.get(pr_number)

        diff_content = ""
        changed_files = []

        changes = mr.changes
        for change in changes:
            if isinstance(change, dict):
                diff_content += change.get("diff", "") + "\n"
                changed_files.append(change.get("new_path", ""))

        return PRMetadata(
            repo_owner=repo_owner,
            repo_name=repo_name,
            pr_number=pr_number,
            title=mr.title,
            description=mr.description or "",
            diff_content=diff_content,
            changed_files=changed_files,
            base_branch=mr.target_branch,
            head_branch=mr.source_branch,
        )

    def validate_token(self) -> bool:
        """Check token has required access."""
        try:
            self._client.user
            return True
        except gitlab.exceptions.GitlabAuthenticationError:
            return False
