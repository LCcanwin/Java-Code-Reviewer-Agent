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


class RunStatus(str, Enum):
    """Overall review run status."""

    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"


class ErrorType(str, Enum):
    """Normalized error categories for recovery and monitoring."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    PROVIDER_AUTH_ERROR = "PROVIDER_AUTH_ERROR"
    PROVIDER_RATE_LIMIT = "PROVIDER_RATE_LIMIT"
    PROVIDER_NOT_FOUND = "PROVIDER_NOT_FOUND"
    PROVIDER_NETWORK_ERROR = "PROVIDER_NETWORK_ERROR"
    DIFF_FETCH_ERROR = "DIFF_FETCH_ERROR"
    RAG_ERROR = "RAG_ERROR"
    LLM_ERROR = "LLM_ERROR"
    LLM_PARSE_ERROR = "LLM_PARSE_ERROR"
    FEEDBACK_REJECTED = "FEEDBACK_REJECTED"
    PATCH_FILE_READ_ERROR = "PATCH_FILE_READ_ERROR"
    PATCH_GENERATION_ERROR = "PATCH_GENERATION_ERROR"
    PATCH_PUSH_ERROR = "PATCH_PUSH_ERROR"
    SECURITY_ERROR = "SECURITY_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class RecoveryActionType(str, Enum):
    """Allowed recovery actions."""

    RETRY = "retry"
    RETRY_WITH_REPAIR_PROMPT = "retry_with_repair_prompt"
    FALLBACK_AUDIT_ONLY = "fallback_audit_only"
    SKIP_NODE = "skip_node"
    PARTIAL_SUCCESS = "partial_success"
    FAIL = "fail"


class Issue(TypedDict):
    """A single code review issue."""

    severity: Severity
    rule_id: str  # e.g., "NAMING-001"
    file_path: str
    line_number: int
    message: str
    code_snippet: str
    suggestion: NotRequired[str]


class NodeResult(TypedDict):
    """Execution metadata for one graph node."""

    status: Literal["success", "failed", "skipped", "retried"]
    duration_ms: int
    retry_count: int
    error_type: NotRequired[str]
    error_message: NotRequired[str]


class ReviewError(TypedDict):
    """Normalized error captured during a review run."""

    node: str
    error_type: str
    message: str
    recoverable: bool


class RecoveryAction(TypedDict):
    """A recorded recovery decision."""

    node: str
    action: str
    reason: str
    retry_count: int


class ReviewState(TypedDict):
    """LangGraph state for the code review pipeline."""

    # Run observability
    run_id: NotRequired[str]
    status: NotRequired[RunStatus]
    current_node: NotRequired[str]
    node_results: NotRequired[dict[str, NodeResult]]
    errors: NotRequired[list[ReviewError]]
    recovery_actions: NotRequired[list[RecoveryAction]]
    failed_node: NotRequired[str]
    failure_type: NotRequired[str]
    failure_message: NotRequired[str]
    pending_recovery: NotRequired[bool]
    recovery_action: NotRequired[str]
    repair_prompt: NotRequired[str]

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
    base_branch: NotRequired[str]
    head_branch: NotRequired[str]
    head_repo_owner: NotRequired[str]
    head_repo_name: NotRequired[str]

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

    # Planning and feedback (for iterative review)
    planning_result: NotRequired[str]  # Planner's review plan
    feedback_iteration: NotRequired[int]  # Iteration counter, default 0
    feedback_approved: NotRequired[bool]  # Whether feedback passed
    feedback_message: NotRequired[str]  # Detailed feedback message

    # Outputs
    markdown_report: str
    patch_files: NotRequired[dict[str, str]]  # file_path -> patched content
    patch_commit_sha: NotRequired[str]
    patch_error: NotRequired[str]

    # Error handling
    error: NotRequired[str]
