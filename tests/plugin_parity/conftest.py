"""Opt-in parity oracle suite for optional native kernel plugins.

This suite is skipped entirely unless ``dependence-forecastability-accel``
(or another ``forecastability.kernels`` entry-point provider) is installed.
It is not executed by core CI.

Plugin maintainers run this suite in their own CI pipeline to verify that
their native implementation produces bit-identical outputs to the Python
reference for every parity gate defined in:
    docs/plan/aux_documents/pbe_f09_native_plugin_design.md §6
"""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(
    items: list[pytest.Item],
    config: pytest.Config,
) -> None:
    """Skip every test in plugin_parity/ if no provider is installed."""
    try:
        from forecastability.ports.kernels import load_kernel_provider

        provider = load_kernel_provider()
        if provider is None:
            raise RuntimeError("no provider")
    except Exception:  # noqa: BLE001
        skip = pytest.mark.skip(
            reason=(
                "No forecastability.kernels entry-point provider installed. "
                "Install dependence-forecastability-accel (or equivalent) to "
                "run the plugin parity suite."
            )
        )
        for item in items:
            if "plugin_parity" in str(item.fspath):
                item.add_marker(skip)
