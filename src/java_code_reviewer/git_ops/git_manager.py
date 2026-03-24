"""Git operations manager using GitPython."""

import os
import tempfile
from pathlib import Path
from typing import Optional

from git import Git, Repo

from ..config import get_config


class GitManager:
    """Manages Git operations for code review patches."""

    def __init__(self):
        cfg = get_config()
        self._clone_depth = cfg.git_clone_depth
        self._branch_prefix = cfg.git_branch_prefix

    @property
    def branch_prefix(self) -> str:
        return self._branch_prefix

    def clone_repo(
        self,
        repo_url: str,
        branch: Optional[str] = None,
        target_dir: Optional[str] = None,
    ) -> str:
        """Clone a repository shallowly."""
        if target_dir is None:
            target_dir = tempfile.mkdtemp()

        git = Git()
        if branch:
            git.clone("--depth", str(self._clone_depth), "--branch", branch, repo_url, target_dir)
        else:
            git.clone("--depth", str(self._clone_depth), repo_url, target_dir)

        return target_dir

    def create_commit(
        self,
        repo_owner: str,
        repo_name: str,
        branch_name: str,
        patch_files: dict[str, str],
        message: str,
    ) -> str:
        """Create a commit with patch files and return commit SHA."""
        repo_url = f"https://github.com/{repo_owner}/{repo_name}.git"
        clone_dir = self.clone_repo(repo_url)

        repo = Repo(clone_dir)

        git = repo.git
        git.checkout("-b", branch_name)

        for filepath, content in patch_files.items():
            full_path = Path(clone_dir) / filepath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            git.add(filepath)

        commit = git.commit("-m", message)
        remote_url = repo.remotes.origin.url.replace("https://", f"https://{get_config().github_token}@")
        repo.remotes.origin.set_url(remote_url)
        git.push("-u", "origin", branch_name)

        return commit.hexsha

    def apply_patch(self, repo_dir: str, patch_content: str) -> None:
        """Apply a patch to a cloned repository."""
        git = Git(repo_dir)
        patch_file = Path(repo_dir) / "review.patch"
        patch_file.write_text(patch_content)
        git.apply(patch_file)
        patch_file.unlink()
