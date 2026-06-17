"""Frozen Pydantic result models for covariant interpretation agent tool returns.

The single tool in
:mod:`forecastability.adapters.agents.runtime.covariant_interpretation_agent`
returns the full :class:`CovariantInterpretationResult` via ``model_dump()``.

Because ``CovariantInterpretationResult`` itself is a frozen Pydantic model,
the simplest type-safe approach is to return it directly.  The model is
re-exported here so all typed tool result types live under one subpackage.

No new fields are added; semantics are unchanged.
"""

from __future__ import annotations

from forecastability.domain.value_objects.types import CovariantInterpretationResult

__all__ = [
    "CovariantInterpretationResult",
]
