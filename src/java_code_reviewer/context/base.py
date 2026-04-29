"""Base interfaces for review context providers."""

from typing import Protocol

from ..state.review_state import ReviewState


class ContextProvider(Protocol):
    """A source that can provide review context keyed by changed file path."""

    name: str

    def retrieve(self, state: ReviewState) -> dict[str, str]:
        """Return context snippets keyed by changed file path."""
        ...
