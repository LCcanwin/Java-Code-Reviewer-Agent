"""Configuration management for Java Code Reviewer Agent."""

import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration loader from config.yaml and environment variables."""

    _instance: Optional["Config"] = None

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config.yaml"
        else:
            config_path = Path(config_path)

        with open(config_path, "r") as f:
            self._cfg = yaml.safe_load(f)

    @classmethod
    def get_instance(cls, config_path: Optional[str] = None) -> "Config":
        """Get singleton config instance."""
        if cls._instance is None:
            cls._instance = cls(config_path)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton (useful for testing)."""
        cls._instance = None

    @property
    def github_token(self) -> Optional[str]:
        return os.getenv(self._cfg["github"]["token_env"])

    @property
    def gitlab_token(self) -> Optional[str]:
        return os.getenv(self._cfg["gitlab"]["token_env"])

    @property
    def github_api_url(self) -> str:
        return self._cfg["github"]["api_url"]

    @property
    def gitlab_api_url(self) -> str:
        return self._cfg["gitlab"]["api_url"]

    @property
    def scope_limit(self) -> list[str]:
        raw = os.getenv("SCOPE_LIMIT", "")
        return [s.strip() for s in raw.split(",") if s.strip()]

    @property
    def llm_provider(self) -> str:
        return os.getenv("LLM_PROVIDER", self._cfg["llm"]["provider"])

    @property
    def llm_api_key(self) -> Optional[str]:
        return os.getenv("LLM_API_KEY")

    @property
    def llm_model(self) -> str:
        return os.getenv("LLM_MODEL", self._cfg["llm"]["model"])

    @property
    def llm_temperature(self) -> float:
        return self._cfg["llm"]["temperature"]

    @property
    def llm_max_tokens(self) -> int:
        return self._cfg["llm"]["max_tokens"]

    @property
    def llm_base_url(self) -> Optional[str]:
        return os.getenv("LLM_BASE_URL")

    @property
    def git_clone_depth(self) -> int:
        return self._cfg["git"]["clone_depth"]

    @property
    def git_branch_prefix(self) -> str:
        return self._cfg["git"]["branch_prefix"]

    @property
    def rag_top_k(self) -> int:
        return self._cfg["rag"]["top_k"]

    @property
    def review_max_files(self) -> int:
        return self._cfg["review"]["max_files"]

    @property
    def review_max_context_lines(self) -> int:
        return self._cfg["review"]["max_context_lines"]


def get_config() -> Config:
    """Get the global config instance."""
    return Config.get_instance()
