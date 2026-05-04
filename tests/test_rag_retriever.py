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


def test_query_expansion_adds_rule_intent_terms():
    kb = _offline_kb()
    retriever = Retriever(kb, top_k=3)
    diff = """--- a/src/OrderService.java
+++ b/src/OrderService.java
@@ -1,2 +1,4 @@
+if (orders.size() > 0) {
+    log.info("has orders");
+}
"""

    queries = retriever._build_queries("src/OrderService.java", diff)
    expanded_query = "\n".join(queries)

    assert "collection emptiness check" in expanded_query
    assert "use isEmpty instead of size comparison" in expanded_query
    assert "集合判空" in expanded_query


def test_retriever_runs_multiple_queries_and_merges_unique_rules():
    class RecordingKnowledgeBase:
        def __init__(self):
            self.queries = []

        def similarity_search(self, query: str, top_k: int = 5):
            self.queries.append(query)
            if "detected risk patterns" in query:
                return [ALIBABA_STANDARDS["CONCURRENCY-003"]]
            if "expanded rule intent" in query:
                return [ALIBABA_STANDARDS["COLLECTION-003"], ALIBABA_STANDARDS["CONCURRENCY-003"]]
            return []

    kb = RecordingKnowledgeBase()
    retriever = Retriever(kb, top_k=3)
    diff = """--- a/src/Worker.java
+++ b/src/Worker.java
@@ -1,2 +1,4 @@
+ExecutorService executor = Executors.newFixedThreadPool(10);
+if (items.size() > 0) {
+}
"""

    context = retriever.retrieve_context("src/Worker.java", diff)

    assert len(kb.queries) > 1
    assert any("detected risk patterns" in query for query in kb.queries)
    assert any("expanded rule intent" in query for query in kb.queries)
    assert context is not None
    assert "CONCURRENCY-003" in context
    assert "COLLECTION-003" in context
    assert context.count("CONCURRENCY-003") == 1
