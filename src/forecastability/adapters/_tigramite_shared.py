"""Shared tigramite internals used by tigramite_adapter and pcmci_ami_adapter."""

from __future__ import annotations

import importlib

#: Tigramite link-type strings that denote a directed causal edge.
_DIRECTED_LINKS: frozenset[str] = frozenset({"-->", "o->", "o-o"})


def _check_tigramite_available() -> None:
    """Raise ImportError if tigramite is not installed."""
    try:
        importlib.import_module("tigramite")
    except ImportError as exc:
        raise ImportError(
            "tigramite is required for PCMCI+ causal discovery. "
            "Install with `uv sync --extra causal` or `pip install tigramite`."
        ) from exc
