"""Shared helpers for Phase 1 performance measurement scripts."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.metadata
import io
import json
import os
import platform
import resource
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, Literal

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

WorkflowName = Literal["run_triage"]
SignalName = Literal["ar1", "seasonal_ar1", "white_noise"]
PublicWorkflowMethod = Literal[
    "import",
    "run_covariant_analysis",
    "run_lagged_exogenous_triage",
    "run_extended_forecastability_analysis",
    "compute_spectral_forecastability",
    "compute_ordinal_complexity",
    "compute_classical_structure",
    "compute_memory_structure",
]


class PerformanceCaseConfig(BaseModel):
    """One deterministic synthetic baseline case."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    size_label: str
    workflow: WorkflowName
    n_obs: int = Field(ge=1)
    max_lag: int = Field(ge=1)
    n_surrogates: int = Field(ge=99)
    compute_significance: bool = False
    signal: SignalName
    random_state: int


class PerformanceMetadataConfig(BaseModel):
    """Top-level metadata for performance outputs."""

    model_config = ConfigDict(frozen=True)

    release: str
    random_state_base: int = 42
    repeats: int = Field(default=3, ge=1)
    output_dir: str = "outputs/performance"
    notes: str = ""


class ProfileConfig(BaseModel):
    """Profiling target selection."""

    model_config = ConfigDict(frozen=True)

    top_n: int = Field(default=25, ge=1)
    enabled_targets: list[str] = Field(default_factory=list)
    profile_size_labels: list[str] = Field(default_factory=lambda: ["small"])


class BudgetEntry(BaseModel):
    """One acceptance budget keyed to a measured baseline."""

    model_config = ConfigDict(frozen=True)

    baseline_wall_s: float = Field(gt=0.0)
    target_max_wall_s: float = Field(gt=0.0)


class Pbef05BudgetsConfig(BaseModel):
    """PBE-F05 acceptance budgets vs Phase 1 medians."""

    model_config = ConfigDict(frozen=True)

    notes: str = ""
    medium_run_triage_with_significance: BudgetEntry
    medium_run_batch_triage: BudgetEntry
    medium_cross_ami: BudgetEntry


class BudgetsConfig(BaseModel):
    """Performance acceptance budgets section."""

    model_config = ConfigDict(frozen=True)

    pbe_f05: Pbef05BudgetsConfig | None = None


class PublicWorkflowConfig(BaseModel):
    """One measured public workflow or import-latency benchmark."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str = ""
    method: PublicWorkflowMethod
    import_statement: str | None = None
    n_series: int | None = Field(default=None, ge=1)
    series_length: int | None = Field(default=None, ge=1)
    max_lag: int | None = Field(default=None, ge=1)
    n_surrogates: int | None = Field(default=None, ge=99)
    significance_mode: Literal["none", "phase"] | None = None
    methods: list[str] | None = None
    signal: SignalName = "seasonal_ar1"
    period: int | None = Field(default=None, gt=1)
    include_ami_geometry: bool = True
    ordinal_embedding_dimension: int = Field(default=3, ge=2)
    ordinal_delay: int = Field(default=1, ge=1)
    memory_min_scale: int | None = Field(default=None, ge=4)
    memory_max_scale: int | None = Field(default=None, ge=5)
    random_state: int = 42

    @model_validator(mode="after")
    def _validate_method_requirements(self) -> PublicWorkflowConfig:
        """Enforce lightweight config invariants per workflow method."""
        if self.method == "import":
            return self

        if self.series_length is None:
            raise ValueError("series_length is required for non-import public workflows")

        if (
            self.method
            in {
                "run_covariant_analysis",
                "run_lagged_exogenous_triage",
            }
            and self.max_lag is None
        ):
            raise ValueError("max_lag is required for multiseries public workflows")

        if self.method == "run_covariant_analysis" and self.significance_mode is None:
            raise ValueError("significance_mode is required for run_covariant_analysis")

        if self.method == "run_lagged_exogenous_triage" and self.significance_mode is None:
            raise ValueError("significance_mode is required for run_lagged_exogenous_triage")

        if self.method == "run_extended_forecastability_analysis" and self.max_lag is None:
            raise ValueError("max_lag is required for run_extended_forecastability_analysis")

        if self.memory_max_scale is not None and self.memory_min_scale is not None:
            if self.memory_max_scale <= self.memory_min_scale:
                raise ValueError("memory_max_scale must be greater than memory_min_scale")
        return self


class PerformanceBaselineConfig(BaseModel):
    """Validated performance baseline YAML config."""

    model_config = ConfigDict(frozen=True)

    metadata: PerformanceMetadataConfig
    cases: list[PerformanceCaseConfig]
    profile: ProfileConfig = Field(default_factory=ProfileConfig)
    budgets: BudgetsConfig | None = None
    public_workflows: list[PublicWorkflowConfig] | None = None


class RuntimeMeasurement(BaseModel):
    """Wall/CPU/memory measurement for one operation."""

    model_config = ConfigDict(frozen=True)

    wall_time_s: float
    cpu_time_s: float
    peak_memory_mb: float


def repo_root() -> Path:
    """Return the repository root for script execution."""
    return Path(__file__).resolve().parents[1]


def load_performance_config(path: Path) -> PerformanceBaselineConfig:
    """Load and validate the Phase 1 performance config."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return PerformanceBaselineConfig.model_validate(payload)


def sha256_bytes(data: bytes) -> str:
    """Return a SHA-256 hex digest for bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    """Return a SHA-256 digest for an existing file, or ``None``."""
    if not path.exists():
        return None
    return sha256_bytes(path.read_bytes())


def git_sha(root: Path) -> str | None:
    """Return the current git commit SHA when available."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def numpy_show_config_digest() -> str:
    """Digest NumPy build configuration, including BLAS/LAPACK details."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        np.show_config()
    return sha256_bytes(buffer.getvalue().encode("utf-8"))


def threadpoolctl_snapshot() -> list[dict[str, Any]] | dict[str, str]:
    """Return threadpoolctl metadata when the sklearn transitive dependency is present."""
    try:
        from threadpoolctl import threadpool_info
    except ImportError:
        return {"unavailable": "threadpoolctl import failed"}
    return threadpool_info()


def cpu_model() -> str:
    """Return a best-effort CPU model string without requiring extra dependencies."""
    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError):
            return platform.processor()
        return result.stdout.strip() or platform.processor()

    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("model name"):
                return line.partition(":")[2].strip()
    return platform.processor()


def _ru_maxrss_to_mb(value: int) -> float:
    """Normalize ``ru_maxrss`` to MiB across macOS and Linux."""
    if sys.platform == "darwin":
        return value / (1024.0 * 1024.0)
    return value / 1024.0


def peak_rss_mb() -> float:
    """Return process peak RSS in MiB."""
    return _ru_maxrss_to_mb(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def runtime_metadata(*, config_path: Path, config_hash: str) -> dict[str, Any]:
    """Build portable command/runtime metadata required by the Phase 1 plan."""
    root = repo_root()
    return {
        "command": " ".join(sys.argv),
        "command_cwd": str(Path.cwd()),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "os": platform.system(),
        "kernel": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_model": cpu_model(),
        "cpu_count": os.cpu_count(),
        "git_sha": git_sha(root),
        "config_path": str(config_path),
        "config_hash": config_hash,
        "numpy_version": np.__version__,
        "numpy_show_config_digest": numpy_show_config_digest(),
        "threadpoolctl_snapshot": threadpoolctl_snapshot(),
        "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
        "mkl_num_threads": os.environ.get("MKL_NUM_THREADS"),
        "forecastability_version": resolve_forecastability_version(),
        "uv_lock_hash": sha256_file(root / "uv.lock"),
    }


def resolve_forecastability_version() -> str:
    """Return the installed or workspace-local forecastability version string."""
    try:
        return importlib.metadata.version("forecastability")
    except importlib.metadata.PackageNotFoundError:
        from forecastability import __version__

        return __version__


def make_synthetic_series(case: PerformanceCaseConfig) -> np.ndarray:
    """Generate deterministic synthetic data for a baseline or profile case."""
    return make_synthetic_series_spec(
        n_obs=case.n_obs,
        signal=case.signal,
        random_state=case.random_state,
    )


def make_synthetic_series_spec(
    *,
    n_obs: int,
    signal: SignalName,
    random_state: int,
) -> np.ndarray:
    """Generate deterministic synthetic data from the shared signal spec."""
    rng = np.random.default_rng(random_state)
    if signal == "white_noise":
        return rng.normal(0.0, 1.0, size=n_obs)

    innovations = rng.normal(0.0, 0.7, size=n_obs)
    series = np.zeros(n_obs, dtype=float)
    for idx in range(1, n_obs):
        series[idx] = 0.68 * series[idx - 1] + innovations[idx]

    if signal == "seasonal_ar1":
        t = np.arange(n_obs, dtype=float)
        series = series + 0.8 * np.sin(2.0 * np.pi * t / 12.0)
    return series


def make_synthetic_exog(series: np.ndarray, *, seed: int) -> np.ndarray:
    """Generate a deterministic lagged exogenous driver for profiling."""
    rng = np.random.default_rng(seed)
    shifted = np.roll(series, 2)
    shifted[:2] = 0.0
    return 0.6 * shifted + rng.normal(0.0, 0.5, size=series.size)


@contextlib.contextmanager
def measured_runtime() -> Iterator[Callable[[], RuntimeMeasurement]]:
    """Context manager returning a measurement factory after the block."""
    wall_start = time.perf_counter()
    cpu_start = time.process_time()
    yield lambda: RuntimeMeasurement(
        wall_time_s=time.perf_counter() - wall_start,
        cpu_time_s=time.process_time() - cpu_start,
        peak_memory_mb=peak_rss_mb(),
    )


def json_default(value: Any) -> Any:
    """JSON serializer for NumPy scalars and arrays in lightweight artifacts."""
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def write_json(path: Path, payload: Any) -> None:
    """Write a stable, indented JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=json_default) + "\n",
        encoding="utf-8",
    )
