"""
Register hyphenated import paths (services/*-service, packages/*-*) for local uvicorn.

Docker images copy folders to underscore names; pytest loads conftest.py automatically.
For local `uvicorn services.auth_service.main:app`, import this module first in-process.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_PACKAGES_DIR = ROOT / "packages"
if str(_PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(_PACKAGES_DIR))

for _svc in ("auth-service", "health-service", "ai-service"):
    _svc_dir = str(ROOT / "services" / _svc)
    if _svc_dir not in sys.path:
        sys.path.insert(0, _svc_dir)


class HyphenatedModuleFinder:
    _NAMESPACE_DIRS: dict[str, Path] = {
        "services": ROOT / "services",
        "packages": ROOT / "packages",
    }

    @classmethod
    def find_spec(cls, fullname, path, target=None):
        parts = fullname.split(".")
        namespace = parts[0]
        if namespace not in cls._NAMESPACE_DIRS or len(parts) < 2:
            return None

        base_dir = cls._NAMESPACE_DIRS[namespace]
        pkg_name = parts[1]
        hyphen_name = pkg_name.replace("_", "-")
        pkg_dir = base_dir / hyphen_name

        if not pkg_dir.exists():
            return None

        subpath = parts[2:]
        if not subpath:
            init_file = pkg_dir / "__init__.py"
            if init_file.exists():
                return importlib.util.spec_from_file_location(
                    fullname, str(init_file), submodule_search_locations=[str(pkg_dir)]
                )
            return importlib.util.spec_from_file_location(
                fullname, None, submodule_search_locations=[str(pkg_dir)]
            )

        target_path = pkg_dir.joinpath(*subpath)
        init_file = target_path / "__init__.py"
        py_file = target_path.with_suffix(".py")

        if target_path.is_dir() and init_file.exists():
            return importlib.util.spec_from_file_location(
                fullname, str(init_file), submodule_search_locations=[str(target_path)]
            )
        if py_file.exists():
            return importlib.util.spec_from_file_location(fullname, str(py_file))
        return None


if not any(isinstance(finder, HyphenatedModuleFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, HyphenatedModuleFinder())
