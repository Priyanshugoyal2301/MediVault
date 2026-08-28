"""Run a MediVault uvicorn service with hyphenated import bootstrap."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bootstrap_imports  # noqa: F401,E402
import uvicorn

_BFF_APPS = frozenset({"apps.api.main:app", "main:app"})


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: python scripts/run_service.py <module:app> <port>\n"
            "Examples:\n"
            "  python scripts/run_service.py services.auth_service.main:app 8001\n"
            "  python scripts/run_service.py apps.api.main:app 8000"
        )
    app_path, port_s = sys.argv[1], sys.argv[2]
    port = int(port_s)
    if app_path in _BFF_APPS:
        api_dir = REPO / "apps" / "api"
        uvicorn.run(
            "main:app",
            host="127.0.0.1",
            port=port,
            log_level="info",
            app_dir=str(api_dir),
        )
        return
    uvicorn.run(app_path, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
