"""LLM client abstraction for OpenAI/Anthropic."""

from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from ..config import get_config


class LLMClient:
    """Abstraction over LLM providers (OpenAI/Anthropic)."""

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        cfg = get_config()
        self._provider = provider or cfg.llm_provider
        self._model = model or cfg.llm_model
        self._temperature = cfg.llm_temperature
        self._max_tokens = cfg.llm_max_tokens
        self._api_key = cfg.llm_api_key
        self._base_url = cfg.llm_base_url

        self._client = self._build_client()

    def _build_client(self):
        """Build the underlying LangChain chat model."""
        if self._provider == "anthropic":
            return ChatAnthropic(
                model=self._model,
                api_key=self._api_key,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
            )
        else:
            return ChatOpenAI(
                model=self._model,
                api_key=self._api_key,
                base_url=self._base_url,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )

    def invoke(self, messages: list[dict]) -> str:
        """Invoke LLM with messages."""
        from langchain_core.messages import HumanMessage, SystemMessage

        langchain_messages = []
        for msg in messages:
            if msg["role"] == "system":
                langchain_messages.append(SystemMessage(content=msg["content"]))
            else:
                langchain_messages.append(HumanMessage(content=msg["content"]))

        response = self._client.invoke(langchain_messages)
        return response.content

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model(self) -> str:
        return self._model
