"""Application-layer validation harnesses and regression helpers.

These modules orchestrate services/use-cases to validate end-to-end behaviour
and rebuild regression fixtures. They live under ``use_cases/`` rather than
``diagnostics/`` because they are application-layer concerns, not numerical
building-blocks.

Kept import-light: submodules are imported directly by their callers rather
than eagerly re-exported here, to avoid pulling the full services/use-case
graph at package import time.
"""

from __future__ import annotations
