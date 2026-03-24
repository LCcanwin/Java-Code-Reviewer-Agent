"""Knowledge base for RAG-based context retrieval."""

from typing import Optional

import faiss
import numpy as np
from langchain_openai import OpenAIEmbeddings

from ..config import get_config
from .alibaba_standards import ALIBABA_STANDARDS, AlibabaStandard


class KnowledgeBase:
    """FAISS-based knowledge base for Alibaba standards."""

    def __init__(self):
        cfg = get_config()
        self._embedding_model = OpenAIEmbeddings(
            model=cfg._cfg["rag"]["embedding_model"],
            api_key=cfg.llm_api_key,
            base_url=cfg.llm_base_url,
        )
        self._index: Optional[faiss.Index] = None
        self._rules: list[AlibabaStandard] = []
        self._rule_texts: list[str] = []
        self._rule_ids: list[str] = []
        self._built = False

    def build_index(self) -> None:
        """Build FAISS index from Alibaba standards."""
        if self._built:
            return

        self._rules = list(ALIBABA_STANDARDS.values())
        self._rule_texts = [
            self._rule_to_text(rule) for rule in self._rules
        ]
        self._rule_ids = [rule.rule_id for rule in self._rules]

        embeddings = self._embedding_model.embed_documents(self._rule_texts)
        embeddings_array = np.array(embeddings).astype("float32")

        dimension = embeddings_array.shape[1]
        self._index = faiss.IndexFlatL2(dimension)
        self._index.add(embeddings_array)

        self._built = True

    def _rule_to_text(self, rule: AlibabaStandard) -> str:
        """Convert a rule to searchable text."""
        examples = "\n".join(f"Example: {ex}" for ex in rule.examples)
        keywords = ", ".join(rule.keywords)
        return (
            f"Rule ID: {rule.rule_id}\n"
            f"Title: {rule.title}\n"
            f"Category: {rule.category}\n"
            f"Severity: {rule.severity}\n"
            f"Description: {rule.description}\n"
            f"{examples}\n"
            f"Keywords: {keywords}"
        )

    def similarity_search(self, query: str, top_k: int = 5) -> list[AlibabaStandard]:
        """Find most similar rules to query."""
        if not self._built:
            self.build_index()

        query_embedding = self._embedding_model.embed_query(query)
        query_vector = np.array([query_embedding]).astype("float32")

        k = min(top_k, len(self._rules))
        distances, indices = self._index.search(query_vector, k)

        results = []
        for idx in indices[0][:k]:
            if idx < len(self._rules):
                results.append(self._rules[idx])

        return results
