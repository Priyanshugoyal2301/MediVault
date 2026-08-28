"""Build semantic retrieval index (configuration-driven)."""

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


def train(config_path: Path | None = None) -> Path:
    from models.retrieval.config_loader import load_config
    from models.retrieval.dataset import ensure_dataset_files
    from models.retrieval.infer import SemanticRetriever, resolve_repo_path

    cfg = load_config(config_path, validate=True)
    ensure_dataset_files(resolve_repo_path(cfg["paths"]["train_data"]))
    retriever = SemanticRetriever(cfg, auto_build_if_missing=True)
    art = retriever.build_index()
    print(
        json.dumps(
            {
                "artifacts": str(art),
                "embedding": retriever.backend_name,
                "vector_store": retriever.store_name,
                "chunks": retriever.index_size,
            },
            indent=2,
        )
    )
    return art


def main() -> None:
    p = argparse.ArgumentParser(description="Train/build semantic retrieval index")
    p.add_argument("--config", type=Path, default=None)
    args = p.parse_args()
    train(args.config)


if __name__ == "__main__":
    main()
