"""Train entrypoint for models/quality — scaffold only.

Do not call this from production services.
When ready, load datasets/*, fit model, write artifacts under ./artifacts/.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Train quality model (scaffold)")
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.yaml")))
    args = parser.parse_args()
    print(f"[quality] train scaffold — config={args.config}")
    print("No training implemented yet. See docs/ml-migration-plan.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
