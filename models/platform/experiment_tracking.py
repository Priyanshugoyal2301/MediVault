"""Optional experiment tracking — disabled by default.

Env:
  ML_EXPERIMENT_TRACKING=0|1
  ML_EXPERIMENT_BACKEND=none|mlflow|wandb
  MLFLOW_TRACKING_URI=...
  WANDB_PROJECT=...
  WANDB_MODE=offline|online|disabled
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Any, Iterator


def tracking_enabled() -> bool:
    return os.getenv("ML_EXPERIMENT_TRACKING", "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def backend_name() -> str:
    if not tracking_enabled():
        return "none"
    return (os.getenv("ML_EXPERIMENT_BACKEND") or "none").strip().lower()


class ExperimentLogger:
    """No-op by default. MLflow or W&B when explicitly enabled."""

    def __init__(self, run_name: str = "medivault_run", params: dict[str, Any] | None = None) -> None:
        self.run_name = run_name
        self.params = params or {}
        self.backend = backend_name()
        self._handle: Any = None
        self._t0 = time.perf_counter()

    def __enter__(self) -> "ExperimentLogger":
        if self.backend == "mlflow":
            try:
                import mlflow

                uri = os.getenv("MLFLOW_TRACKING_URI")
                if uri:
                    mlflow.set_tracking_uri(uri)
                exp = os.getenv("MLFLOW_EXPERIMENT_NAME", "medivault")
                mlflow.set_experiment(exp)
                self._handle = mlflow.start_run(run_name=self.run_name)
                if self.params:
                    mlflow.log_params({k: str(v)[:250] for k, v in self.params.items()})
            except Exception:
                self.backend = "none"
                self._handle = None
        elif self.backend == "wandb":
            try:
                import wandb

                mode = os.getenv("WANDB_MODE", "offline")
                self._handle = wandb.init(
                    project=os.getenv("WANDB_PROJECT", "medivault"),
                    name=self.run_name,
                    config=self.params,
                    mode=mode,
                    reinit=True,
                )
            except Exception:
                self.backend = "none"
                self._handle = None
        return self

    def log_metrics(self, metrics: dict[str, float], step: int | None = None) -> None:
        if self.backend == "none":
            return
        try:
            if self.backend == "mlflow":
                import mlflow

                mlflow.log_metrics({k: float(v) for k, v in metrics.items()}, step=step)
            elif self.backend == "wandb" and self._handle is not None:
                import wandb

                payload = dict(metrics)
                if step is not None:
                    payload["step"] = step
                wandb.log(payload)
        except Exception:
            pass

    def log_artifact(self, path: str) -> None:
        if self.backend == "none":
            return
        try:
            if self.backend == "mlflow":
                import mlflow

                mlflow.log_artifact(path)
            elif self.backend == "wandb" and self._handle is not None:
                import wandb

                wandb.save(path)
        except Exception:
            pass

    def __exit__(self, *exc) -> None:
        if self.backend == "mlflow" and self._handle is not None:
            try:
                import mlflow

                mlflow.log_metric("wall_time_s", time.perf_counter() - self._t0)
                mlflow.end_run()
            except Exception:
                pass
        if self.backend == "wandb" and self._handle is not None:
            try:
                import wandb

                wandb.finish()
            except Exception:
                pass


@contextmanager
def experiment_run(
    run_name: str = "medivault_run", params: dict[str, Any] | None = None
) -> Iterator[ExperimentLogger]:
    with ExperimentLogger(run_name, params) as log:
        yield log
