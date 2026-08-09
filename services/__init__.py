"""
services/__init__.py — Dynamic package alias for hyphenated service directories.

Allows `import services.auth_service`, `services.ai_service`, and `services.health_service`
to resolve to the corresponding hyphenated disk directories:
  services/auth-service
  services/ai-service
  services/health-service

This is used by the pytest test suite to keep imports readable while preserving
Python package naming conventions (underscores) vs filesystem conventions (hyphens).
"""

import importlib.util
import sys
from pathlib import Path

_SERVICES_DIR = Path(__file__).parent


def __getattr__(name: str):
    """Dynamically resolve `services.<name>` → `services/<name-with-hyphens>`."""
    hyphen_name = name.replace("_", "-")
    target_dir = _SERVICES_DIR / hyphen_name
    if target_dir.is_dir():
        init_file = target_dir / "__init__.py"
        full_name = f"services.{name}"
        spec = importlib.util.spec_from_file_location(
            full_name,
            str(init_file) if init_file.exists() else None,
            submodule_search_locations=[str(target_dir)],
        )
        if spec:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[full_name] = mod
            if spec.loader and init_file.exists():
                spec.loader.exec_module(mod)
            return mod
    raise AttributeError(f"module 'services' has no attribute '{name}'")
