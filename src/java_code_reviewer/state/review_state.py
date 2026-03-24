"""ReviewState TypedDict and enums for LangGraph state machine."""

from enum import Enum
from typing import Literal, TypedDict

from typing_extensions import NotRequired


class ReviewMode(str, Enum):
    """Review mode selection."""

    AUDIT_ONLY = "audit_only"
    AUTOFIX = "autofix"


class Severity(str, Enum):
    """Issue severity levels based on Alibaba standards."""

    BLOCKER = "blocker"  # Must fix (强制)
    CRITICAL = "critical"  # Strongly recommended (推荐)
    WARNING = "warning"  # Advisory (参考)
    INFO = "info"  # Informational


class Issue(TypedDict):
    """A single code review issue."""

    severity: Severity
    rule_id: str  # e.g., "NAMING-001"
    file_path: str
    line_number: int
    message: str
    code_snippet: str
    suggestion: NotRequired[str]


class ReviewState(TypedDict):
    """LangGraph state for the code review pipeline."""

    # Input
    pr_url: str
    mode: ReviewMode

    # Validated metadata
    validated: bool
    validation_error: NotRequired[str]

    # PR identification
    provider: Literal["github", "gitlab"]
    repo_owner: str
    repo_name: str
    pr_number: int

    # PR content
    diff_content: str
    changed_files: list[str]
    pr_title: str
    pr_description: str

    # RAG context (file path -> relevant code)
    retrieved_context: dict[str, str]

    # Review results
    issues: list[Issue]

    # Routing
    route_decision: Literal["report", "patch"]

    # Outputs
    markdown_report: str
    patch_files: NotRequired[dict[str, str]]  # file_path -> patched content
    patch_commit_sha: NotRequired[str]
    patch_error: NotRequired[str]

    # Error handling
    error: NotRequired[str]
