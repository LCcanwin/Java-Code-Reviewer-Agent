"""Utilities for merging context from multiple providers."""

from collections import defaultdict


class ContextMerger:
    """Merge provider contexts with deterministic ordering and size limits."""

    def __init__(self, max_chars_per_file: int = 6000):
        self._max_chars_per_file = max_chars_per_file

    def merge(self, provider_contexts: list[tuple[str, dict[str, str]]]) -> dict[str, str]:
        """Merge contexts keyed by file path.

        Contexts are appended in provider order and truncated per file to avoid
        overloading downstream LLM prompts.
        """
        grouped: dict[str, list[str]] = defaultdict(list)

        for provider_name, context in provider_contexts:
            for filepath, content in context.items():
                if not content:
                    continue
                grouped[filepath].append(f"### Source: {provider_name}\n{content.strip()}")

        merged: dict[str, str] = {}
        for filepath, parts in grouped.items():
            content = "\n\n".join(parts)
            merged[filepath] = self._truncate(content)

        return merged

    def _truncate(self, content: str) -> str:
        if len(content) <= self._max_chars_per_file:
            return content
        marker = "\n\n[Context truncated]"
        return content[: max(0, self._max_chars_per_file - len(marker))] + marker
