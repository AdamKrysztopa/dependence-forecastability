"""Deterministic-first routing-validation agent review example (plan v0.3.3 V3_4-F09).

The default path prints the deterministic routing-validation payload only, so
the example runs on a clean checkout without the ``agent`` extra or provider
credentials. The optional ``--live`` flag asks the live narration adapter to
add a narrative downstream of the already-computed bundle.

Usage::

    uv run python examples/univariate/agents/routing_validation_agent_review.py
    uv run python examples/univariate/agents/routing_validation_agent_review.py --smoke
    OPENAI_API_KEY=sk-... uv run python \
        examples/univariate/agents/routing_validation_agent_review.py --live
"""

from __future__ import annotations

import argparse
import asyncio

from forecastability import RoutingPolicyAuditConfig, run_routing_validation
from forecastability.adapters.agents.routing_validation_agent_payload_models import (
    routing_validation_agent_payload,
)
from forecastability.adapters.llm.routing_validation_agent import (
    run_routing_validation_agent,
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI flags for the routing-validation agent example.

    Args:
        argv: Optional argv list for testability.

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(
        description="Deterministic-first routing-validation agent review example"
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run the synthetic panel at n_per_archetype=200",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Request optional live narration after building the deterministic payload",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Optional provider:model identifier for the live path",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the routing-validation agent example.

    Args:
        argv: Optional argv list for testability.

    Returns:
        POSIX-style exit code.
    """
    args = _parse_args(argv)
    bundle = run_routing_validation(
        n_per_archetype=200 if args.smoke else 600,
        real_panel_path=None,
        config=RoutingPolicyAuditConfig(),
    )

    if not args.live:
        payload = routing_validation_agent_payload(bundle)
        print(payload.model_dump_json(indent=2))
        return 0

    explanation = asyncio.run(
        run_routing_validation_agent(
            bundle,
            strict=False,
            model=args.model,
        )
    )
    print(explanation.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
