"""
conftest.py — Root pytest configuration & dynamic module resolution

Resolves module imports like `services.auth_service`, `services.ai_service`, and `services.health_service`
to their hyphenated directory names on disk (`services/auth-service`, `services/ai-service`, `services/health-service`).
"""

import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Ensure root directory is on sys.path
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ensure packages/ is on sys.path so `from packages.shared_utils import ...` works
# without the package being formally installed.
_PACKAGES_DIR = ROOT / "packages"
if str(_PACKAGES_DIR) not in sys.path:
    sys.path.insert(0, str(_PACKAGES_DIR))

# Ensure each service package dir is accessible directly too (for internal imports)
for _svc in ("auth-service", "health-service", "ai-service"):
    _svc_dir = str(ROOT / "services" / _svc)
    if _svc_dir not in sys.path:
        sys.path.insert(0, _svc_dir)


class HyphenatedModuleFinder:
    """
    Custom meta path finder that maps underscore module names to hyphenated
    folder names on disk under services/ and packages/.

    Examples:
      services.auth_service   → services/auth-service/
      services.health_service → services/health-service/
      packages.shared_utils   → packages/shared-utils/
    """

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
        pkg_name = parts[1]                       # e.g., auth_service / shared_utils
        hyphen_name = pkg_name.replace("_", "-")  # e.g., auth-service / shared-utils
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
            else:
                return importlib.util.spec_from_file_location(
                    fullname, None, submodule_search_locations=[str(pkg_dir)]
                )
        else:
            target_path = pkg_dir.joinpath(*subpath)
            init_file = target_path / "__init__.py"
            py_file = target_path.with_suffix(".py")

            if target_path.is_dir() and init_file.exists():
                return importlib.util.spec_from_file_location(
                    fullname, str(init_file), submodule_search_locations=[str(target_path)]
                )
            elif py_file.exists():
                return importlib.util.spec_from_file_location(fullname, str(py_file))

        return None


# Insert custom module finder into sys.meta_path
if not any(isinstance(finder, HyphenatedModuleFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, HyphenatedModuleFinder)
