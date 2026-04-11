"""Summary assembler — reserved for future extraction.

Inspection finding
------------------
``types.py`` contains only pure Pydantic data containers (``CanonicalSummary``,
``CanonicalExampleResult``, etc.) with no classmethods or assembly logic.
``CanonicalSummary`` is populated directly by ``aggregation.summarize_canonical_result``,
which already lives in an appropriate standalone module.

No extraction is needed at this time.  Add ``assemble_canonical_summary`` here
if ``CanonicalSummary`` ever acquires a complex construction classmethod that
should be decoupled from the model definition.
"""

from __future__ import annotations

__all__: list[str] = []
