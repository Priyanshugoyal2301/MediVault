"""Train image quality model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    import conftest  # noqa: F401
except Exception:
    pass


def train(config_path: Path | None = None, backend: str | None = None) -> Path:
    from models.image_quality.backends import describe_backends
    from models.image_quality.config_loader import load_config
    from models.image_quality.dataset import ensure_dataset_meta
    from models.image_quality.infer import ImageQualityEngine

    cfg = load_config(config_path, validate=True)
    if backend:
        cfg["active_backend"] = backend
    ensure_dataset_meta()
    eng = ImageQualityEngine(cfg, auto_train_if_missing=False)
    art = eng.train()
    print(
        json.dumps(
            {
                "artifacts": str(art),
                "backend": eng.backend_name,
                "available": describe_backends(),
            },
            indent=2,
        )
    )
    return art


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, default=None)
    p.add_argument("--backend", default=None)
    args = p.parse_args()
    train(args.config, args.backend)


if __name__ == "__main__":
    main()
