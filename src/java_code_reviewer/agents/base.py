"""Abstract base class for PR agents."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PRMetadata:
    """Pull request metadata."""

    repo_owner: str
    repo_name: str
    pr_number: int
    title: str
    description: str
    diff_content: str
    changed_files: list[str]
    base_branch: str
    head_branch: str


class PRAgent(ABC):
    """Abstract interface for interacting with PR providers."""

    @abstractmethod
    def fetch_pr_metadata(self, repo_owner: str, repo_name: str, pr_number: int) -> PRMetadata:
        """Fetch PR metadata including diff and changed files."""
        pass

    @abstractmethod
    def validate_token(self) -> bool:
        """Validate that the API token has required permissions."""
        pass
