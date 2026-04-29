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
        return os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")

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

    @property
    def context_max_chars_per_file(self) -> int:
        return self._cfg.get("context", {}).get("max_chars_per_file", 6000)

    @property
    def alibaba_rules_context_enabled(self) -> bool:
        return self._context_provider_cfg("alibaba_rules").get("enabled", True)

    @property
    def repo_index_mcp_enabled(self) -> bool:
        env_value = os.getenv("REPO_INDEX_MCP_ENABLED")
        if env_value is not None:
            return env_value.lower() in {"1", "true", "yes", "on"}
        return self._context_provider_cfg("repo_index_mcp").get("enabled", False)

    @property
    def repo_index_mcp_server(self) -> str:
        return os.getenv(
            "REPO_INDEX_MCP_SERVER",
            self._context_provider_cfg("repo_index_mcp").get("server", "code_search"),
        )

    @property
    def repo_index_mcp_max_files(self) -> int:
        return self._context_provider_cfg("repo_index_mcp").get("max_files", 20)

    @property
    def repo_index_mcp_max_snippets_per_file(self) -> int:
        return self._context_provider_cfg("repo_index_mcp").get("max_snippets_per_file", 5)

    @property
    def repo_index_mcp_include_tests(self) -> bool:
        return self._context_provider_cfg("repo_index_mcp").get("include_tests", True)

    @property
    def repo_index_mcp_include_references(self) -> bool:
        return self._context_provider_cfg("repo_index_mcp").get("include_references", True)

    @property
    def repo_index_mcp_include_related_files(self) -> bool:
        return self._context_provider_cfg("repo_index_mcp").get("include_related_files", True)

    def _context_provider_cfg(self, provider_name: str) -> dict:
        return self._cfg.get("context", {}).get("providers", {}).get(provider_name, {})


def get_config() -> Config:
    """Get the global config instance."""
    return Config.get_instance()
