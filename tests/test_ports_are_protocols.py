"""Verify every port in ports/ is a runtime-checkable Protocol."""

import ast
from pathlib import Path
from typing import Protocol

from forecastability.ports import (
    CurveComputePort,
    InterpretationPort,
    RecommendationPort,
    ReportRendererPort,
    SeriesValidatorPort,
    SettingsPort,
    SignificanceBandsPort,
)

_ALL_PORTS = [
    SeriesValidatorPort,
    CurveComputePort,
    SignificanceBandsPort,
    InterpretationPort,
    RecommendationPort,
    ReportRendererPort,
    SettingsPort,
]


def test_all_ports_are_protocols() -> None:
    for port in _ALL_PORTS:
        assert issubclass(port, Protocol), f"{port.__name__} must be a Protocol"


def test_all_ports_are_runtime_checkable() -> None:
    # Python 3.11 sets _is_runtime_protocol (not __runtime_checkable__) on the class
    for port in _ALL_PORTS:
        assert getattr(port, "_is_runtime_protocol", False), (
            f"{port.__name__} must be decorated with @runtime_checkable"
        )


def test_no_concrete_imports_in_ports() -> None:
    """Ports module must not import concrete infrastructure packages."""
    ports_file = Path("src/forecastability/ports/__init__.py")
    tree = ast.parse(ports_file.read_text())
    forbidden = {"pydantic_ai", "fastapi", "mcp", "httpx", "click", "typer", "matplotlib"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                assert top not in forbidden, f"ports/__init__.py must not import {top!r}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                assert top not in forbidden, f"ports/__init__.py must not import {top!r}"
