"""Tests for infrastructure settings layer (AGT-002)."""

from __future__ import annotations

from typing import runtime_checkable  # noqa: F401

import pytest
from pydantic import ValidationError

from forecastability.adapters.settings import InfraSettings
from forecastability.ports import SettingsPort


def _make_settings(**overrides: object) -> InfraSettings:
    """Instantiate InfraSettings with no .env contamination."""
    return InfraSettings(_env_file=None, **overrides)  # type: ignore[call-arg]


def test_defaults_load_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _SETTINGS_KEYS = (
        "CONTEXT7",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "XAI_API_KEY",
        "XAI_MODEL",
        "TRIAGE_ENABLE_STREAMING",
        "TRIAGE_DEFAULT_SIGNIFICANCE_MODE",
        "MCP_HOST",
        "MCP_PORT",
    )
    for key in _SETTINGS_KEYS:
        monkeypatch.delenv(key, raising=False)
    settings = _make_settings()
    assert settings.openai_api_key is None
    assert settings.openai_model == "gpt-4o"
    assert settings.triage_enable_streaming is False
    assert settings.triage_default_significance_mode == "surrogate"
    assert settings.mcp_host == "localhost"
    assert settings.mcp_port == 8000


def test_env_override_applied() -> None:
    settings = _make_settings(openai_model="gpt-4-turbo", mcp_port=9000)
    assert settings.openai_model == "gpt-4-turbo"
    assert settings.mcp_port == 9000


def test_invalid_port_type_raises() -> None:
    with pytest.raises(ValidationError):
        _make_settings(mcp_port="not-an-int")


def test_satisfies_settings_port_protocol() -> None:
    """InfraSettings must structurally satisfy SettingsPort."""
    settings = _make_settings()
    # SettingsPort is runtime_checkable — direct isinstance works
    assert isinstance(settings, SettingsPort)


def test_getter_methods_return_correct_values() -> None:
    settings = _make_settings(openai_api_key="sk-test", mcp_port=1234)
    assert settings.get_openai_api_key() == "sk-test"
    assert settings.get_openai_model() == "gpt-4o"
    assert settings.get_triage_enable_streaming() is False
    assert settings.get_triage_default_significance_mode() == "surrogate"
    assert settings.get_mcp_host() == "localhost"
    assert settings.get_mcp_port() == 1234
