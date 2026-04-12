"""Concrete CheckpointPort adapters for durable triage execution (AGT-014).

Two adapters are provided:

- :class:`NoopCheckpointAdapter` — no-op, every load returns ``None``.
- :class:`FilesystemCheckpointAdapter` — writes JSON to a configurable
  directory, keyed by ``checkpoint_key``.

Adapters are confined to this module; use-case code depends only on
:class:`~forecastability.ports.CheckpointPort`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class NoopCheckpointAdapter:
    """Checkpoint adapter that never persists state.

    ``load_checkpoint`` always returns ``None`` so the full pipeline runs
    from scratch on every call.  Use when durability is not required.
    """

    def load_checkpoint(self, checkpoint_key: str) -> dict[str, Any] | None:  # noqa: ARG002
        """Return ``None`` — no checkpoint stored."""
        return None

    def save_checkpoint(
        self,
        checkpoint_key: str,  # noqa: ARG002
        stage: str,  # noqa: ARG002
        state: dict[str, Any],  # noqa: ARG002
    ) -> None:
        """Silently discard the checkpoint."""


class FilesystemCheckpointAdapter:
    """Checkpoint adapter that persists partial triage state to a JSON file.

    Each ``checkpoint_key`` maps to a single ``<checkpoint_dir>/<key>.json``
    file.  The file is overwritten atomically at every stage so the latest
    committed stage is always readable.

    Args:
        checkpoint_dir: Directory where checkpoint files are stored.  Created
            on first use if it does not exist.

    Example::

        from pathlib import Path
        from forecastability.adapters.checkpoint import FilesystemCheckpointAdapter

        adapter = FilesystemCheckpointAdapter(Path("/tmp/triage_checkpoints"))
        adapter.save_checkpoint("run-1", "readiness", {"status": "clear"})
        state = adapter.load_checkpoint("run-1")
        # state == {"stage": "readiness", "data": {"status": "clear"}}
    """

    def __init__(self, checkpoint_dir: Path) -> None:
        self._dir = checkpoint_dir

    def _path(self, checkpoint_key: str) -> Path:
        return self._dir / f"{checkpoint_key}.json"

    def load_checkpoint(self, checkpoint_key: str) -> dict[str, Any] | None:
        """Load checkpoint state for *checkpoint_key*.

        Returns:
            Persisted state dict, or ``None`` when no checkpoint exists.
        """
        path = self._path(checkpoint_key)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            raw: dict[str, Any] = json.load(fh)
        return raw

    def save_checkpoint(
        self,
        checkpoint_key: str,
        stage: str,
        state: dict[str, Any],
    ) -> None:
        """Persist *state* for *checkpoint_key* at *stage*.

        The checkpoint directory is created if it does not already exist.
        Writes are performed via a temp-rename pattern for atomicity.

        Args:
            checkpoint_key: Unique identifier for this triage run.
            stage: Name of the last completed stage.
            state: Serialisable dict of the partial triage state.
        """
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._path(checkpoint_key)
        tmp_path = path.with_suffix(".tmp")
        payload: dict[str, Any] = {"stage": stage, "data": state}
        with tmp_path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        tmp_path.replace(path)
