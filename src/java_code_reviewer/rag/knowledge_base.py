"""Knowledge base for RAG-based context retrieval."""

import logging
import re
from typing import Optional

import faiss
import numpy as np
from langchain_openai import OpenAIEmbeddings

from ..config import get_config
from .alibaba_standards import ALIBABA_STANDARDS, AlibabaStandard

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """FAISS-based knowledge base for Alibaba standards."""

    def __init__(self):
        cfg = get_config()
        self._embedding_model: Optional[OpenAIEmbeddings] = None
        self._embedding_model_name = cfg._cfg["rag"]["embedding_model"]
        self._api_key = cfg.llm_api_key
        self._base_url = cfg.llm_base_url
        self._index: Optional[faiss.Index] = None
        self._rules: list[AlibabaStandard] = []
        self._rule_texts: list[str] = []
        self._rule_ids: list[str] = []
        self._built = False
        self._embedding_failed = False

    def build_index(self) -> None:
        """Build FAISS index from Alibaba standards."""
        if self._built:
            return

        self._rules = list(ALIBABA_STANDARDS.values())
        self._rule_texts = [
            self._rule_to_text(rule) for rule in self._rules
        ]
        self._rule_ids = [rule.rule_id for rule in self._rules]

        try:
            embedding_model = self._get_embedding_model()
            embeddings = embedding_model.embed_documents(self._rule_texts)
            embeddings_array = np.array(embeddings).astype("float32")

            dimension = embeddings_array.shape[1]
            self._index = faiss.IndexFlatL2(dimension)
            self._index.add(embeddings_array)

            self._built = True
        except Exception as e:
            logger.warning(f"Failed to build embedding index: {e}, using default rules")
            self._embedding_failed = True
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
            f"Source: {rule.source}\n"
            f"Version: {rule.version}\n"
            f"Section: {rule.section}\n"
            f"Level: {rule.level}\n"
            f"Description: {rule.description}\n"
            f"{examples}\n"
            f"Keywords: {keywords}\n"
            f"Detection Patterns: {', '.join(rule.detection_patterns)}"
        )

    def similarity_search(self, query: str, top_k: int = 5) -> list[AlibabaStandard]:
        """Find most similar rules to query."""
        if not self._built:
            self.build_index()

        keyword_ranked = self._keyword_search(query)

        if self._embedding_failed or self._index is None:
            return keyword_ranked[:top_k] if keyword_ranked else self._rules[:top_k]

        try:
            embedding_model = self._get_embedding_model()
            query_embedding = embedding_model.embed_query(query)
            query_vector = np.array([query_embedding]).astype("float32")

            k = min(max(top_k * 2, top_k), len(self._rules))
            distances, indices = self._index.search(query_vector, k)

            vector_ranked = []
            for idx in indices[0][:k]:
                if 0 <= idx < len(self._rules):
                    vector_ranked.append(self._rules[idx])

            return self._merge_rankings(keyword_ranked, vector_ranked, top_k)
        except Exception as e:
            logger.warning(f"Embedding query failed: {e}, returning default rules")
            return keyword_ranked[:top_k] if keyword_ranked else self._rules[:top_k]

    def _keyword_search(self, query: str) -> list[AlibabaStandard]:
        """Rank rules by keyword and pattern hits against the query."""
        query_lower = query.lower()
        scored: list[tuple[int, AlibabaStandard]] = []

        for rule in self._rules:
            score = 0
            for keyword in rule.keywords:
                if keyword.lower() in query_lower:
                    score += 3
            for pattern in rule.detection_patterns:
                try:
                    if re.search(pattern, query, flags=re.MULTILINE):
                        score += 5
                except re.error:
                    if pattern.lower() in query_lower:
                        score += 2
            if rule.category.lower() in query_lower:
                score += 1
            if score:
                scored.append((score, rule))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [rule for _, rule in scored]

    def _merge_rankings(
        self,
        keyword_ranked: list[AlibabaStandard],
        vector_ranked: list[AlibabaStandard],
        top_k: int,
    ) -> list[AlibabaStandard]:
        """Merge keyword and vector results while keeping keyword hits first."""
        results: list[AlibabaStandard] = []
        seen: set[str] = set()

        for rule in keyword_ranked + vector_ranked:
            if rule.rule_id in seen:
                continue
            results.append(rule)
            seen.add(rule.rule_id)
            if len(results) >= top_k:
                break

        return results

    def _get_embedding_model(self) -> OpenAIEmbeddings:
        """Lazily initialize embeddings so keyword fallback works without API keys."""
        if self._embedding_model is None:
            self._embedding_model = OpenAIEmbeddings(
                model=self._embedding_model_name,
                api_key=self._api_key,
                base_url=self._base_url,
            )
        return self._embedding_model
