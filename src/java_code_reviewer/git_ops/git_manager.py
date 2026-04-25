"""Git operations manager using GitPython."""

import shutil
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

        try:
            git = Git()
            if branch:
                git.clone("--depth", str(self._clone_depth), "--branch", branch, repo_url, target_dir)
            else:
                git.clone("--depth", str(self._clone_depth), repo_url, target_dir)
        finally:
            pass  # Caller is responsible for cleanup if target_dir was generated

        return target_dir

    def create_commit(
        self,
        repo_owner: str,
        repo_name: str,
        branch_name: str,
        patch_files: dict[str, str],
        message: str,
        provider: str = "github",
    ) -> str:
        """Create a commit with patch files and return commit SHA."""
        if provider == "gitlab":
            repo_url = f"https://gitlab.com/{repo_owner}/{repo_name}.git"
        else:
            repo_url = f"https://github.com/{repo_owner}/{repo_name}.git"
        clone_dir = self.clone_repo(repo_url)

        try:
            repo = Repo(clone_dir)

            git = repo.git
            git.checkout("-b", branch_name)

            clone_root = Path(clone_dir).resolve()
            for filepath, content in patch_files.items():
                full_path = (clone_root / filepath).resolve()
                try:
                    full_path.relative_to(clone_root)
                except ValueError as exc:
                    raise ValueError(f"Patch file escapes repository: {filepath}") from exc

                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
                git.add(filepath)

            commit = git.commit("-m", message)
            token = get_config().gitlab_token if provider == "gitlab" else get_config().github_token
            if token:
                username = "oauth2" if provider == "gitlab" else "x-access-token"
                remote_url = repo.remotes.origin.url.replace("https://", f"https://{username}:{token}@")
                repo.remotes.origin.set_url(remote_url)
            git.push("-u", "origin", branch_name)

            return commit.hexsha
        finally:
            shutil.rmtree(clone_dir, ignore_errors=True)

    def apply_patch(self, repo_dir: str, patch_content: str) -> None:
        """Apply a patch to a cloned repository."""
        git = Git(repo_dir)
        patch_file = Path(repo_dir) / "review.patch"
        patch_file.write_text(patch_content)
        git.apply(patch_file)
        patch_file.unlink()
