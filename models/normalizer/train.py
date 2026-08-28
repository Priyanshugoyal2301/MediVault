"""Train the medical test normalizer (configuration-driven)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure repo root on path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def train(config_path: Path | None = None, backend: str | None = None) -> Path:
    from models.normalizer.config_loader import artifacts_dir, load_config
    from models.normalizer.dataset import ensure_dataset_files, load_train_pairs
    from models.normalizer.encoder_backends import create_backend
    from models.normalizer.preprocess import preprocess_test_name

    cfg = load_config(config_path, validate=True)
    if backend:
        cfg["active_backend"] = backend

    # Config paths like ../../datasets/... are relative to models/normalizer/
    data_dir = Path(cfg["paths"]["train_data"])
    if not data_dir.is_absolute():
        data_dir = (Path(__file__).resolve().parent / data_dir).resolve()
    ensure_dataset_files(data_dir)

    kind = (cfg.get("active_backend") or "char_tfidf").lower()
    if kind in ("modernbert", "clinicalbert", "primary", "fallback_hf"):
        if not cfg.get("allow_hf_download"):
            print(
                "HF backend requested without NORMALIZER_ALLOW_HF=1 — "
                "training char_tfidf instead (deploy-safe)."
            )
            kind = "char_tfidf"
            cfg["active_backend"] = kind

    pairs = load_train_pairs(data_dir)
    texts: list[str] = []
    labels: list[str] = []
    for p in pairs:
        if p.get("unknown"):
            continue
        raw = preprocess_test_name(str(p.get("raw") or ""))
        canon = str(p.get("canonical") or "")
        if raw and canon:
            texts.append(raw)
            labels.append(canon)

    backend_obj = create_backend(kind, cfg)
    backend_obj.fit(texts, labels)
    art = artifacts_dir(cfg)
    backend_obj.save(art)
    meta = {
        "backend": kind,
        "n_pairs": len(texts),
        "n_labels": len(set(labels)),
        "artifacts": str(art),
        "primary_architecture": cfg.get("primary_architecture"),
        "fallback_architecture": cfg.get("fallback_architecture"),
        "offline_architecture": cfg.get("offline_architecture"),
    }
    (art / "train_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))
    return art


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Medical Test Normalizer")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument(
        "--backend",
        type=str,
        default=None,
        help="char_tfidf | modernbert | clinicalbert",
    )
    args = parser.parse_args()
    train(args.config, args.backend)


if __name__ == "__main__":
    main()
