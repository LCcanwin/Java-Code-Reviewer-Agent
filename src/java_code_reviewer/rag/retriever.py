"""Retriever for fetching relevant context from knowledge base."""

from typing import Optional

from .alibaba_standards import AlibabaStandard
from .knowledge_base import KnowledgeBase


class Retriever:
    """Retrieve relevant Alibaba standards context for code review."""

    def __init__(self, knowledge_base: KnowledgeBase, top_k: int = 5):
        self._kb = knowledge_base
        self._top_k = top_k

    def retrieve_context(self, filepath: str, diff_content: str) -> Optional[str]:
        """Retrieve relevant standards context for a file."""
        queries = self._build_queries(filepath, diff_content)
        if not queries:
            return None

        rules = self._retrieve_rules(queries)

        if not rules:
            return None

        context_parts = []
        for rule in rules:
            context_parts.append(self._format_rule_context(rule))

        return "\n\n".join(context_parts)

    def _build_query(self, filepath: str, diff_content: str) -> str:
        """Build a combined retrieval query for backward-compatible callers."""
        return "\n\n".join(self._build_queries(filepath, diff_content))

    def _build_queries(self, filepath: str, diff_content: str) -> list[str]:
        """Build multiple focused queries from file path, symbols, added code, and expanded intents."""
        symbols = self._extract_symbols(filepath, diff_content)
        added_lines = self._extract_added_lines(diff_content)
        added_code = "\n".join(added_lines)
        risk_patterns = self._extract_risk_patterns(added_code)
        expansion_terms = self._expand_query_terms(filepath, added_code, risk_patterns)

        query_specs = [
            ["detected risk patterns", *risk_patterns],
            ["expanded rule intent", *expansion_terms],
            ["added java code", *added_lines[:80]],
            ["java symbols", *symbols[:20]],
            ["file context", filepath],
        ]

        queries = []
        seen = set()
        for parts in query_specs:
            query = "\n".join(part for part in parts if part).strip()
            if query and query not in seen:
                queries.append(query)
                seen.add(query)

        return queries

    def _retrieve_rules(self, queries: list[str]) -> list[AlibabaStandard]:
        """Run multiple focused searches and merge unique rules in ranking order."""
        rules: list[AlibabaStandard] = []
        seen: set[str] = set()

        for query in queries:
            for rule in self._kb.similarity_search(query, self._top_k):
                if rule.rule_id in seen:
                    continue
                rules.append(rule)
                seen.add(rule.rule_id)
                if len(rules) >= self._top_k:
                    return rules

        return rules

    def _extract_symbols(self, filepath: str, diff_content: str) -> list[str]:
        """Extract Java symbols (class names, method names) from diff."""
        import re

        symbols: list[str] = []

        class_pattern = re.compile(r"(?:public|private|protected)?\s*(?:static)?\s*class\s+(\w+)")
        method_pattern = re.compile(r"(?:public|private|protected)?\s*(?:static)?\s*[\w<>\[\]]+\s+(\w+)\s*\(")
        interface_pattern = re.compile(r"(?:public|private|protected)?\s*interface\s+(\w+)")

        for line in diff_content.split("\n"):
            if class_match := class_pattern.search(line):
                symbols.append(class_match.group(1))
            if method_match := method_pattern.search(line):
                symbols.append(method_match.group(1))
            if interface_match := interface_pattern.search(line):
                symbols.append(interface_match.group(1))

        return symbols[:20]

    def _extract_added_lines(self, diff_content: str) -> list[str]:
        """Extract added code lines from unified diff content."""
        lines = []
        for line in diff_content.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                stripped = line[1:].strip()
                if stripped:
                    lines.append(stripped)
        return lines

    def _extract_risk_patterns(self, code: str) -> list[str]:
        """Extract high-signal code patterns for rules retrieval."""
        import re

        checks = [
            (r"catch\s*\([^)]*Exception[^)]*\)", "catch Exception"),
            (r"finally\s*\{[\s\S]*?return\b", "finally return"),
            (r"Executors\.new\w+ThreadPool", "Executors thread pool"),
            (r"ThreadLocal", "ThreadLocal remove"),
            (r"\.size\(\)\s*(?:==|>|!=)\s*0", "collection size empty check"),
            (r"(?i)select\s+\*", "SELECT *"),
            (r"(?i)select\s+count\s*\(", "SELECT COUNT"),
            (r"\b(?:boolean|Boolean)\s+is[A-Z]\w*", "POJO boolean is prefix"),
            (r"for\s*\([^:]+:\s*[^)]+\)\s*\{[\s\S]*?\.remove\(", "foreach remove"),
        ]

        patterns = []
        for pattern, label in checks:
            if re.search(pattern, code):
                patterns.append(label)
        return patterns

    def _expand_query_terms(self, filepath: str, code: str, risk_patterns: list[str]) -> list[str]:
        """Expand concrete Java syntax into standard-rule retrieval terms."""
        import re

        text = f"{filepath}\n{code}\n{' '.join(risk_patterns)}"
        checks = [
            (
                r"\.size\(\)\s*(?:==|>|!=)\s*0|collection size empty check",
                [
                    "collection emptiness check",
                    "use isEmpty instead of size comparison",
                    "集合判空",
                    "isEmpty()",
                ],
            ),
            (
                r"catch\s*\([^)]*(?:Exception|RuntimeException)[^)]*\)|catch Exception",
                [
                    "exception handling",
                    "generic exception catch",
                    "catch specific exception",
                    "异常捕获",
                ],
            ),
            (
                r"finally\s*\{[\s\S]*?return\b|finally return",
                [
                    "finally block return",
                    "do not return in finally",
                    "finally吞异常",
                ],
            ),
            (
                r"Executors\.new\w+ThreadPool|Executors thread pool",
                [
                    "thread pool creation",
                    "use ThreadPoolExecutor instead of Executors",
                    "线程池创建",
                ],
            ),
            (
                r"ThreadLocal",
                [
                    "ThreadLocal cleanup",
                    "ThreadLocal remove",
                    "memory leak prevention",
                ],
            ),
            (
                r"(?i)select\s+\*|SELECT \*",
                [
                    "SQL explicit columns",
                    "avoid SELECT star",
                    "SQL返回列",
                ],
            ),
            (
                r"(?i)select\s+count\s*\(|SELECT COUNT",
                [
                    "SQL existence check",
                    "use EXISTS or LIMIT 1 instead of count",
                    "SQL存在性判断",
                ],
            ),
            (
                r"\b(?:boolean|Boolean)\s+is[A-Z]\w*|POJO boolean is prefix",
                [
                    "POJO boolean field naming",
                    "boolean property should not use is prefix",
                    "布尔属性命名",
                ],
            ),
            (
                r"for\s*\([^:]+:\s*[^)]+\)\s*\{[\s\S]*?\.remove\(|foreach remove",
                [
                    "collection remove during foreach",
                    "use Iterator remove",
                    "集合遍历删除",
                ],
            ),
            (
                r"new\s+(?:ArrayList|HashMap)\s*<[^>]*>\s*\(\s*\)",
                [
                    "collection initial capacity",
                    "ArrayList HashMap capacity",
                    "集合初始化容量",
                ],
            ),
        ]

        expansions: list[str] = []
        seen = set()
        for pattern, terms in checks:
            if not re.search(pattern, text, flags=re.MULTILINE):
                continue
            for term in terms:
                if term not in seen:
                    expansions.append(term)
                    seen.add(term)

        return expansions

    def _format_rule_context(self, rule: AlibabaStandard) -> str:
        """Format a rule for inclusion in context."""
        examples = "\n".join(f"  - {ex}" for ex in rule.examples)
        patterns = "\n".join(f"  - {pattern}" for pattern in rule.detection_patterns)
        return (
            f"**{rule.rule_id}: {rule.title}** [{rule.severity}]\n"
            f"Source: {rule.source} | Version: {rule.version} | Section: {rule.section} | Level: {rule.level}\n"
            f"{rule.description}\n"
            f"Examples:\n{examples}\n"
            f"Detection hints:\n{patterns}"
        )
