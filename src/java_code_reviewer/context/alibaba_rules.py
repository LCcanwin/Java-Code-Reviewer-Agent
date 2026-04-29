"""Alibaba standards context provider."""

from ..config import get_config
from ..rag.knowledge_base import KnowledgeBase
from ..rag.retriever import Retriever
from ..state.review_state import ReviewState


class AlibabaRulesProvider:
    """Retrieve Alibaba Java standards relevant to changed files."""

    name = "alibaba_rules"

    def retrieve(self, state: ReviewState) -> dict[str, str]:
        changed_files = state.get("changed_files", [])
        diff_content = state.get("diff_content", "")
        if not changed_files:
            return {}

        cfg = get_config()
        kb = KnowledgeBase()
        retriever = Retriever(kb, top_k=cfg.rag_top_k)

        context: dict[str, str] = {}
        for filepath in changed_files[: cfg.review_max_files]:
            file_context = retriever.retrieve_context(filepath, diff_content)
            if file_context:
                context[filepath] = f"## Alibaba Rules\n\n{file_context}"

        return context
