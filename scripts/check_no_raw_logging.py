#!/usr/bin/env python3
"""
Check that no Python file outside packages/shared-utils/logging.py
uses bare 'import logging'.

All services must use:
    from packages.shared_utils import get_logger
    logger = get_logger(__name__)

Exit 0 if clean, exit 1 with failures listed.
Used as a pre-commit hook (receives changed file paths as argv).
"""

import re
import sys
from pathlib import Path

# Pattern: bare 'import logging' on its own line (not 'from logging import ...')
_PATTERN = re.compile(r"^\s*import logging\s*(?:#.*)?$", re.MULTILINE)

# Files allowed to use stdlib logging directly (the implementation itself)
_ALLOWED_SUFFIXES = {
    "packages/shared-utils/logging.py",
    "packages\\shared-utils\\logging.py",
}


def _is_allowed(path_str: str) -> bool:
    return any(path_str.replace("\\", "/").endswith(a.replace("\\", "/")) for a in _ALLOWED_SUFFIXES)


def main() -> int:
    paths = sys.argv[1:]
    if not paths:
        # When run without args (e.g. manually), scan the whole repo
        root = Path(__file__).parent.parent
        paths = [str(p) for p in root.rglob("*.py")]

    failures: list[str] = []
    for path_str in paths:
        if _is_allowed(path_str):
            continue
        try:
            content = Path(path_str).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if _PATTERN.search(content):
            failures.append(path_str)

    if failures:
        print(
            "\n[ERROR] Bare 'import logging' found in the following files.\n"
            "Use 'from packages.shared_utils import get_logger' instead.\n"
            "See packages/shared-utils/README.md for the correct pattern.\n"
        )
        for f in failures:
            print(f"  {f}")
        print()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
