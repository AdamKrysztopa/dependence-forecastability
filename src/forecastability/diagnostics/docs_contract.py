"""Docs-contract type definitions for forecastability.

Provides the canonical enumeration of docs-contract sub-check names used by
``scripts/check_docs_contract.py`` and any tooling that references them.
"""

from __future__ import annotations

from typing import Literal

DocsCheckName = Literal[
    "import-contract",
    "version-coherence",
    "terminology",
    "plan-lifecycle",
    "no-framework-imports",
    "root-path-pinned",
]

__all__ = ["DocsCheckName"]
