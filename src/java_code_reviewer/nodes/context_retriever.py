"""Context retriever node - collect review context from configured providers."""

from ..config import get_config
from ..context import AlibabaRulesProvider, ContextMerger, ContextProvider, RepoIndexMCPProvider
from ..observability import redact_secrets
from ..state.review_state import ErrorType, ReviewState


def context_retriever_node(state: ReviewState) -> ReviewState:
    """Retrieve and merge context for changed files."""
    changed_files = state.get("changed_files", [])

    if not changed_files:
        state["retrieved_context"] = {}
        state["repo_context"] = {}
        state["context_sources"] = []
        state["context_errors"] = []
        return state

    cfg = get_config()
    providers = _build_providers()
    provider_contexts: list[tuple[str, dict[str, str]]] = []
    context_sources: list[str] = []
    context_errors = []
    repo_context: dict[str, str] = {}

    for provider in providers:
        try:
            context = provider.retrieve(state)
        except Exception as exc:
            context_errors.append(
                {
                    "node": "context_retriever",
                    "error_type": ErrorType.RAG_ERROR.value,
                    "message": f"{provider.name} failed: {redact_secrets(exc)}",
                    "recoverable": True,
                }
            )
            continue

        if not context:
            continue

        provider_contexts.append((provider.name, context))
        context_sources.append(provider.name)
        if provider.name == "repo_index_mcp":
            repo_context.update(context)

    merger = ContextMerger(max_chars_per_file=cfg.context_max_chars_per_file)
    state["retrieved_context"] = merger.merge(provider_contexts)
    state["repo_context"] = repo_context
    state["context_sources"] = context_sources
    state["context_errors"] = context_errors
    return state


def _build_providers() -> list[ContextProvider]:
    cfg = get_config()
    providers: list[ContextProvider] = []

    if cfg.alibaba_rules_context_enabled:
        providers.append(AlibabaRulesProvider())

    if cfg.repo_index_mcp_enabled:
        providers.append(RepoIndexMCPProvider())

    return providers
