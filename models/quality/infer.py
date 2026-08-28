"""Inference entrypoint for models/quality — scaffold only."""
from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Infer with quality model (scaffold)")
    parser.add_argument("--input", required=False, help="Path to input sample")
    args = parser.parse_args()
    print(f"[quality] infer scaffold — input={args.input}")
    print("No weights loaded. Production path uses default adapters.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
