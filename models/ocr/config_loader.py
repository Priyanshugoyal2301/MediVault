"""
Unlimited-OCR configuration load + fail-fast validation (Phase 1A).

Prevents invalid backend combinations and accidental multi-GB model downloads.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_CONFIG_PATH = Path(__file__).with_name("config.yaml")

VALID_BACKENDS = frozenset({"auto", "http", "local", "stub"})


class UnlimitedOCRConfigError(ValueError):
    """Invalid OCR configuration — fail fast before inference."""


def _truthy(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def load_config(path: str | Path | None = None, *, validate: bool = True) -> dict[str, Any]:
    cfg_path = Path(path) if path else _CONFIG_PATH
    data: dict[str, Any] = {}
    if cfg_path.exists():
        raw = cfg_path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw) or {}

    backend = os.getenv("UNLIMITED_OCR_BACKEND", data.get("backend", "auto")).strip().lower()
    data["backend"] = backend

    http = dict(data.get("http") or {})
    endpoint = os.getenv("UNLIMITED_OCR_ENDPOINT", http.get("endpoint") or "").strip()
    http["endpoint"] = endpoint
    if os.getenv("UNLIMITED_OCR_TIMEOUT_S"):
        http["timeout_s"] = float(os.getenv("UNLIMITED_OCR_TIMEOUT_S", "120"))
    data["http"] = http

    local = dict(data.get("local") or {})
    if os.getenv("UNLIMITED_OCR_DEVICE"):
        local["device"] = os.getenv("UNLIMITED_OCR_DEVICE")
    # Phase 1A: local weights require explicit opt-in (prevent hang/OOM)
    local["allow_local_weights"] = _truthy("UNLIMITED_OCR_ALLOW_LOCAL_WEIGHTS", "0")
    local["allow_download"] = _truthy("UNLIMITED_OCR_ALLOW_LOCAL_DOWNLOAD", "0")
    data["local"] = local

    if os.getenv("UNLIMITED_OCR_HF_MODEL"):
        data["hf_model_id"] = os.getenv("UNLIMITED_OCR_HF_MODEL")

    # Fallback policy knobs
    data["treat_empty_lab_as_failure"] = _truthy(
        "UNLIMITED_OCR_EMPTY_AS_FAILURE",
        "1",  # default ON for production-safe fallback
    )

    if validate:
        validate_config(data)
    return data


def validate_config(config: dict[str, Any]) -> None:
    backend = (config.get("backend") or "auto").lower()
    if backend not in VALID_BACKENDS:
        raise UnlimitedOCRConfigError(
            f"Invalid UNLIMITED_OCR_BACKEND={backend!r}; "
            f"allowed={sorted(VALID_BACKENDS)}"
        )

    http = config.get("http") or {}
    endpoint = (http.get("endpoint") or "").strip()
    timeout = float(http.get("timeout_s") or 120)
    if timeout <= 0 or timeout > 3600:
        raise UnlimitedOCRConfigError(
            f"UNLIMITED_OCR_TIMEOUT_S must be in (0, 3600], got {timeout}"
        )

    local = config.get("local") or {}
    allow_local = bool(local.get("allow_local_weights"))
    allow_download = bool(local.get("allow_download"))

    if backend == "http" and not endpoint:
        # Fail at validation only when explicitly http (auto may degrade at runtime)
        raise UnlimitedOCRConfigError(
            "UNLIMITED_OCR_BACKEND=http requires UNLIMITED_OCR_ENDPOINT"
        )

    if backend == "local" and not allow_local:
        raise UnlimitedOCRConfigError(
            "UNLIMITED_OCR_BACKEND=local requires "
            "UNLIMITED_OCR_ALLOW_LOCAL_WEIGHTS=1 "
            "(prevents accidental multi-GB downloads/OOM)"
        )

    if backend == "local" and allow_download is True:
        # allowed but discouraged — still ok
        pass

    if backend == "auto":
        # Phase 1A: auto NEVER selects local. HTTP if endpoint present, else fail at runtime → legacy.
        # Document this policy; validation passes with or without endpoint.
        pass


def describe_config(config: dict[str, Any]) -> dict[str, Any]:
    """Safe summary for logs (no secrets)."""
    http = config.get("http") or {}
    local = config.get("local") or {}
    endpoint = (http.get("endpoint") or "").strip()
    return {
        "backend": config.get("backend"),
        "http_endpoint_configured": bool(endpoint),
        "http_timeout_s": http.get("timeout_s"),
        "allow_local_weights": bool(local.get("allow_local_weights")),
        "allow_local_download": bool(local.get("allow_download")),
        "treat_empty_lab_as_failure": bool(config.get("treat_empty_lab_as_failure", True)),
        "hf_model_id": config.get("hf_model_id"),
    }


def readiness_check(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Startup / health readiness (does not load model weights).
    Returns {ready, mode, reason, config_summary}.
    """
    try:
        cfg = config or load_config(validate=True)
    except UnlimitedOCRConfigError as exc:
        return {
            "ready": False,
            "mode": "misconfigured",
            "reason": str(exc),
            "config_summary": {},
        }

    backend = (cfg.get("backend") or "auto").lower()
    endpoint = ((cfg.get("http") or {}).get("endpoint") or "").strip()
    summary = describe_config(cfg)

    if backend == "stub":
        return {
            "ready": True,
            "mode": "stub",
            "reason": "stub backend for CI (not production VLM)",
            "config_summary": summary,
        }
    if backend == "http":
        return {
            "ready": True,
            "mode": "http",
            "reason": "HTTP endpoint configured",
            "config_summary": summary,
        }
    if backend == "local":
        return {
            "ready": True,
            "mode": "local",
            "reason": "local weights explicitly allowed (load deferred to first request)",
            "config_summary": summary,
        }
    # auto
    if endpoint:
        return {
            "ready": True,
            "mode": "auto-http",
            "reason": "auto will use HTTP endpoint only",
            "config_summary": summary,
        }
    return {
        "ready": False,
        "mode": "auto-unready",
        "reason": (
            "auto backend with no UNLIMITED_OCR_ENDPOINT; "
            "requests will fall back to legacy (local weights never auto-selected)"
        ),
        "config_summary": summary,
    }
