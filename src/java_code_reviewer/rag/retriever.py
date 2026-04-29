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
        query = self._build_query(filepath, diff_content)
        if not query:
            return None

        rules = self._kb.similarity_search(query, self._top_k)

        if not rules:
            return None

        context_parts = []
        for rule in rules:
            context_parts.append(self._format_rule_context(rule))

        return "\n\n".join(context_parts)

    def _build_query(self, filepath: str, diff_content: str) -> str:
        """Build a retrieval query from file path, symbols, added code, and risk patterns."""
        symbols = self._extract_symbols(filepath, diff_content)
        added_lines = self._extract_added_lines(diff_content)
        risk_patterns = self._extract_risk_patterns("\n".join(added_lines))

        query_parts = [filepath]
        query_parts.extend(symbols[:20])
        query_parts.extend(risk_patterns)
        query_parts.extend(added_lines[:80])

        return "\n".join(part for part in query_parts if part).strip()

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
