"""Train entrypoint for Unlimited-OCR fine-tuning — Phase 1 scaffold only.

Phase 1 does not train. Use this entrypoint in later phases to fine-tune on
datasets/document_parsing labeled scans. Live inference uses baidu/Unlimited-OCR
weights or a remote endpoint.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Train Unlimited-OCR (not active in Phase 1)")
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.yaml")))
    args = parser.parse_args()
    print(f"[ocr] train scaffold — config={args.config}")
    print(
        "Phase 1: no training. Deploy baidu/Unlimited-OCR via UNLIMITED_OCR_ENDPOINT "
        "or UNLIMITED_OCR_BACKEND=local after accepting model license/weight download."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
