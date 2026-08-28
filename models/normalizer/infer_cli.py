"""CLI entry for single-string or batch normalization."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Infer canonical lab test names")
    parser.add_argument("names", nargs="*", help="Raw test name(s)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from models.normalizer.infer import MedicalTestNormalizer

    norm = MedicalTestNormalizer()
    names = args.names or ["HGB", "SGPT", "HbA1c"]
    results = [norm.normalize(n).to_dict() for n in names]
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(
                f"{r['raw_name']!r} → {r['canonical_name']} "
                f"({r['confidence']:.1%}) LOINC={r['loinc']} [{r['status']}]"
            )


if __name__ == "__main__":
    main()
