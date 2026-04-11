"""Report payload assembler — reserved for future extraction.

Inspection finding
------------------
``reporting.py`` exposes only small, focused module-level functions
(``build_canonical_markdown``, ``save_canonical_result_json``,
``build_benchmark_markdown``, ``build_exog_group_markdown``, etc.).
None of these are classmethods or staticmethods baked into domain models,
and none construct large intermediate dict payloads worthy of a dedicated
assembler at this stage.

No extraction is needed at this time.  Add assembly helpers here if
``reporting.py`` grows complex multi-step payload construction that
should be unit-tested in isolation from the file I/O layer.
"""

from __future__ import annotations

__all__: list[str] = []
