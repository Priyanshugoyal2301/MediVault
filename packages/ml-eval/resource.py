"""Resource / runtime measurement helpers for model evaluation."""

from __future__ import annotations

import os
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any, Callable, TypeVar

T = TypeVar("T")


def resource_snapshot() -> dict[str, float]:
    """
    Best-effort process memory snapshot (MiB).

    Uses tracemalloc peak if tracing is active; otherwise returns 0.0 for peak.
    """
    current = 0.0
    peak = 0.0
    if tracemalloc.is_tracing():
        cur, pk = tracemalloc.get_traced_memory()
        current = cur / (1024 * 1024)
        peak = pk / (1024 * 1024)
    rss = 0.0
    try:
        import resource  # Unix only

        # ru_maxrss is KiB on Linux, bytes on macOS — report as MiB best-effort
        rss_raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform == "darwin":
            rss = rss_raw / (1024 * 1024)
        else:
            rss = rss_raw / 1024.0
    except Exception:  # noqa: BLE001
        rss = 0.0
    return {
        "memory_current_mib": round(current, 4),
        "memory_peak_mib": round(peak, 4),
        "memory_rss_mib": round(rss, 4),
    }


def measure_model_size_bytes(path: str | Path | None) -> int:
    """Total bytes of a model file or directory tree. 0 if path is missing."""
    if path is None:
        return 0
    p = Path(path)
    if not p.exists():
        return 0
    if p.is_file():
        return p.stat().st_size
    total = 0
    for root, _dirs, files in os.walk(p):
        for name in files:
            fp = Path(root) / name
            try:
                total += fp.stat().st_size
            except OSError:
                continue
    return total


def timed(fn: Callable[[], T], *, repeats: int = 1) -> tuple[T, float]:
    """
    Run fn `repeats` times; return last result and mean wall-clock time in ms.
    """
    if repeats < 1:
        raise ValueError("repeats must be >= 1")
    result: T | None = None
    times: list[float] = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        result = fn()
        times.append((time.perf_counter() - t0) * 1000.0)
    assert result is not None
    return result, sum(times) / len(times)


def with_memory(fn: Callable[[], T]) -> tuple[T, dict[str, float]]:
    """Run fn under tracemalloc and return result + memory snapshot."""
    was_tracing = tracemalloc.is_tracing()
    if not was_tracing:
        tracemalloc.start()
    try:
        result = fn()
        snap = resource_snapshot()
    finally:
        if not was_tracing:
            tracemalloc.stop()
    return result, snap
