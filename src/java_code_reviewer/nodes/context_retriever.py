"""Context retriever node - RAG lookup for diff symbols."""

from typing import Optional

from ..config import get_config
from ..rag.knowledge_base import KnowledgeBase
from ..rag.retriever import Retriever


def context_retriever_node(state: ReviewState) -> ReviewState:
    """Retrieve relevant context from knowledge base for changed files."""
    changed_files = state.get("changed_files", [])
    diff_content = state.get("diff_content", "")

    if not changed_files:
        state["retrieved_context"] = {}
        return state

    cfg = get_config()
    kb = KnowledgeBase()
    retriever = Retriever(kb, top_k=cfg.rag_top_k)

    context: dict[str, str] = {}

    for filepath in changed_files[: cfg.review_max_files]:
        file_context = retriever.retrieve_context(filepath, diff_content)
        if file_context:
            context[filepath] = file_context

    state["retrieved_context"] = context
    return state
