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
        symbols = self._extract_symbols(filepath, diff_content)
        if not symbols:
            return None

        query = " ".join(symbols[:10])
        rules = self._kb.similarity_search(query, self._top_k)

        if not rules:
            return None

        context_parts = []
        for rule in rules:
            context_parts.append(self._format_rule_context(rule))

        return "\n\n".join(context_parts)

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

    def _format_rule_context(self, rule: AlibabaStandard) -> str:
        """Format a rule for inclusion in context."""
        examples = "\n".join(f"  - {ex}" for ex in rule.examples)
        return (
            f"**{rule.rule_id}: {rule.title}** [{rule.severity}]\n"
            f"{rule.description}\n"
            f"Examples:\n{examples}"
        )
