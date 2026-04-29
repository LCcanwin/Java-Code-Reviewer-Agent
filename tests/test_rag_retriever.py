"""Unit tests for RAG retrieval quality."""

from java_code_reviewer.rag.knowledge_base import KnowledgeBase
from java_code_reviewer.rag.retriever import Retriever
from java_code_reviewer.rag.alibaba_standards import ALIBABA_STANDARDS


def _offline_kb() -> KnowledgeBase:
    kb = KnowledgeBase()
    kb._rules = list(ALIBABA_STANDARDS.values())
    kb._built = True
    kb._embedding_failed = True
    return kb


def test_keyword_search_prioritizes_high_signal_patterns():
    kb = _offline_kb()

    results = kb.similarity_search("Executors.newFixedThreadPool(10)", top_k=3)

    assert results
    assert results[0].rule_id == "CONCURRENCY-003"


def test_retriever_uses_added_lines_and_outputs_source_metadata():
    kb = _offline_kb()
    retriever = Retriever(kb, top_k=3)
    diff = """--- a/src/UserMapper.java
+++ b/src/UserMapper.java
@@ -1,2 +1,3 @@
+String sql = "SELECT * FROM users";
"""

    context = retriever.retrieve_context("src/UserMapper.java", diff)

    assert context is not None
    assert "SQL-002" in context
    assert "Source: Alibaba Java Development Manual" in context
    assert "Version:" in context
    assert "Detection hints:" in context
