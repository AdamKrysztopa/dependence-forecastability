"""A4 runnable live screening-agent example with deterministic fallback.

This entrypoint demonstrates how to:
1. Create small deterministic target and candidate arrays.
2. Construct ``ScreeningDeps``.
3. Create the live screening agent from
   ``forecastability.adapters.llm.screening_agent``.
4. Run it when ``pydantic-ai`` and ``OPENAI_API_KEY`` are available.
5. Emit a deterministic fallback message when unavailable.

Usage:
    uv run python examples/covariant_informative/agents/a4_screening_live_agent_demo.py
"""

from __future__ import annotations

import asyncio

import numpy as np

from forecastability.adapters.llm.screening_agent import (
    ScreeningDeps,
    create_screening_agent,
    pydantic_ai_available,
)
from forecastability.adapters.settings import InfraSettings

_DETERMINISTIC_FALLBACK_MESSAGE = (
    "Live screening is unavailable in this runtime. "
    "Deterministic fallback: install optional agent dependencies with "
    "`uv sync --extra agent` and set OPENAI_API_KEY to enable live execution."
)


def _build_demo_arrays() -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Create a small deterministic target and candidate set."""
    rng = np.random.default_rng(42)
    n_samples = 220

    target = np.zeros(n_samples, dtype=float)
    target[0] = rng.standard_normal()
    for idx in range(1, n_samples):
        target[idx] = 0.82 * target[idx - 1] + 0.35 * rng.standard_normal()

    candidates = {
        "driver_strong": np.roll(target, 1) + 0.18 * rng.standard_normal(n_samples),
        "driver_moderate": np.roll(target, 3) + 0.45 * rng.standard_normal(n_samples),
        "driver_weak": rng.standard_normal(n_samples),
    }
    return target, candidates


def _has_openai_key(settings: InfraSettings) -> bool:
    """Return whether a non-empty OpenAI API key is configured."""
    key = settings.get_openai_api_key()
    return key is not None and key.strip() != ""


async def _run_live_agent(*, deps: ScreeningDeps, settings: InfraSettings) -> None:
    """Execute live screening and print the structured report."""
    agent = create_screening_agent(settings=settings)
    result = await agent.run(
        (
            "Screen all candidate features. Assess the target first, then rank "
            "features by peak CrossAMI with concise caveats."
        ),
        deps=deps,
    )
    print("Live screening report:")
    print(result.output.model_dump_json(indent=2))


def main() -> None:
    """Run the A4 screening demo with deterministic fallback behavior."""
    target, candidates = _build_demo_arrays()
    deps = ScreeningDeps(
        target_name="demo_target",
        target=target,
        candidates=candidates,
        max_lag=24,
        n_surrogates=99,
        random_state=42,
    )

    settings = InfraSettings()
    if not pydantic_ai_available() or not _has_openai_key(settings):
        print(_DETERMINISTIC_FALLBACK_MESSAGE)
        print("Constructed ScreeningDeps for target:", deps.target_name)
        print("Candidate features:", ", ".join(sorted(deps.candidates)))
        return

    asyncio.run(_run_live_agent(deps=deps, settings=settings))


if __name__ == "__main__":
    main()
