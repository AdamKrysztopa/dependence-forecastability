"""Infrastructure configuration loaded from environment / .env file."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class InfraSettings(BaseSettings):
    """Typed settings model for runtime infrastructure configuration.

    Scientific parameters (n_neighbors, n_surrogates, alpha, random_state)
    are intentionally absent — they live in configs/*.yaml, not here.

    All fields are optional (defaulted) so that the scientific core remains
    runnable without any .env file. Required keys fail fast with a clear
    ValidationError when an invalid type is supplied.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Context7 (library docs MCP) — env var name is CONTEXT7
    context7: str | None = None

    # OpenAI
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"

    # Anthropic
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5"

    # xAI (Grok)
    xai_api_key: str | None = None
    xai_model: str = "grok-3"

    # Triage behaviour
    triage_enable_streaming: bool = False
    triage_default_significance_mode: str = "surrogate"

    # MCP server
    mcp_host: str = "localhost"
    mcp_port: int = 8000

    def get_context7_api_key(self) -> str | None:
        """Return the Context7 API key, or None if not configured."""
        return self.context7

    def get_openai_api_key(self) -> str | None:
        """Return the OpenAI API key, or None if not configured."""
        return self.openai_api_key

    def get_openai_model(self) -> str:
        """Return the configured OpenAI model identifier."""
        return self.openai_model

    def get_anthropic_api_key(self) -> str | None:
        """Return the Anthropic API key, or None if not configured."""
        return self.anthropic_api_key

    def get_anthropic_model(self) -> str:
        """Return the configured Anthropic model identifier."""
        return self.anthropic_model

    def get_xai_api_key(self) -> str | None:
        """Return the xAI API key, or None if not configured."""
        return self.xai_api_key

    def get_xai_model(self) -> str:
        """Return the configured xAI model identifier."""
        return self.xai_model

    def get_triage_enable_streaming(self) -> bool:
        """Return whether streaming is enabled for triage."""
        return self.triage_enable_streaming

    def get_triage_default_significance_mode(self) -> str:
        """Return the default significance mode for triage ('surrogate' or 'none')."""
        return self.triage_default_significance_mode

    def get_mcp_host(self) -> str:
        """Return the MCP server hostname."""
        return self.mcp_host

    def get_mcp_port(self) -> int:
        """Return the MCP server port."""
        return self.mcp_port
