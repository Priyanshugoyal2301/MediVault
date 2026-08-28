"""
Unlimited-OCR inference backends (Phase 1A hardened).

Modes:
  auto  — HTTP only when endpoint set; NEVER auto-selects local weights (hang/OOM safe)
  http  — remote OpenAI-compatible server only
  local — only with UNLIMITED_OCR_ALLOW_LOCAL_WEIGHTS=1; downloads require separate opt-in
  stub  — CI / offline

Failure always raises UnlimitedOCRError so outer FallbackDocumentParser → legacy.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

from .preprocess import PageImage
from .schema import BoundingBox


class UnlimitedOCRError(RuntimeError):
    """Raised when Unlimited-OCR cannot produce usable page texts."""


@dataclass
class OCRPageResult:
    page_number: int
    raw_text: str
    ocr_confidence: float | None = None
    boxes: list[BoundingBox] | None = None


class UnlimitedOCRClient:
    """Facade over HTTP / local / stub engines."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.backend = (config.get("backend") or "auto").lower()
        self.last_backend_used: str | None = None
        self.last_duration_ms: float | None = None

    def run(self, pages: list[PageImage]) -> list[OCRPageResult]:
        if not pages:
            raise UnlimitedOCRError("No pages to OCR")

        order = self._resolve_backends()
        if not order:
            raise UnlimitedOCRError(
                "No Unlimited-OCR backend available "
                f"(backend={self.backend}; configure UNLIMITED_OCR_ENDPOINT "
                "or UNLIMITED_OCR_BACKEND=stub|local with allow flags)"
            )

        errors: list[str] = []
        for name in order:
            t0 = time.perf_counter()
            try:
                if name == "http":
                    result = self._run_http(pages)
                elif name == "local":
                    result = self._run_local(pages)
                elif name == "stub":
                    result = self._run_stub(pages)
                else:
                    continue
                self.last_backend_used = name
                self.last_duration_ms = (time.perf_counter() - t0) * 1000.0
                if not result or not any((r.raw_text or "").strip() for r in result):
                    raise UnlimitedOCRError(f"{name} returned empty OCR text")
                return result
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{name}: {type(exc).__name__}: {exc}")
                continue
        raise UnlimitedOCRError(
            "Unlimited-OCR backends exhausted; " + "; ".join(errors)
        )

    def _resolve_backends(self) -> list[str]:
        b = self.backend
        if b in ("http", "local", "stub"):
            return [b]
        # auto (Phase 1A): HTTP only — never cascade into local weight load
        http_ep = (self.config.get("http") or {}).get("endpoint") or ""
        if http_ep.strip():
            return ["http"]
        return []

    # ------------------------------------------------------------------ HTTP
    def _run_http(self, pages: list[PageImage]) -> list[OCRPageResult]:
        http = self.config.get("http") or {}
        endpoint = (http.get("endpoint") or "").strip()
        if not endpoint:
            raise UnlimitedOCRError("UNLIMITED_OCR_ENDPOINT / http.endpoint not set")

        multi = len(pages) > 1
        prompt = (
            http.get("prompt_multi") if multi else http.get("prompt_single")
        ) or (" Multi page parsing." if multi else " document parsing.")
        if not prompt.startswith(" "):
            prompt = " " + prompt.lstrip()

        ngram = int(http.get("ngram_size") or 35)
        window = int(
            http.get("window_size_multi") if multi else http.get("window_size_single")
            or (1024 if multi else 128)
        )
        timeout = float(http.get("timeout_s") or 120)
        model = http.get("model") or "Unlimited-OCR"

        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for p in pages:
            b64 = base64.b64encode(p.to_png_bytes()).decode("ascii")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                }
            )

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0.0,
            "skip_special_tokens": False,
            "custom_params": {"ngram_size": ngram, "window_size": window},
        }
        body = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
        except TimeoutError as exc:
            raise UnlimitedOCRError(f"HTTP OCR timeout after {timeout}s") from exc
        except urlerror.URLError as exc:
            raise UnlimitedOCRError(f"HTTP OCR request failed: {exc}") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise UnlimitedOCRError(
                f"HTTP OCR returned malformed JSON: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise UnlimitedOCRError("HTTP OCR JSON root must be an object")

        text = _extract_chat_text(data)
        if not text or not text.strip():
            raise UnlimitedOCRError(
                "HTTP OCR returned empty text (check prompt prefix / logits processor)"
            )

        if len(pages) == 1:
            return [
                OCRPageResult(
                    page_number=pages[0].page_number,
                    raw_text=text,
                    ocr_confidence=0.9,
                )
            ]
        chunks = _split_multi_page(text, len(pages))
        return [
            OCRPageResult(
                page_number=pages[i].page_number,
                raw_text=chunks[i],
                ocr_confidence=0.9,
            )
            for i in range(len(pages))
        ]

    # ---------------------------------------------------------------- Local
    def _run_local(self, pages: list[PageImage]) -> list[OCRPageResult]:
        local = self.config.get("local") or {}
        if not local.get("allow_local_weights"):
            raise UnlimitedOCRError(
                "Local backend disabled; set UNLIMITED_OCR_ALLOW_LOCAL_WEIGHTS=1"
            )

        model_id = self.config.get("hf_model_id") or "baidu/Unlimited-OCR"
        multi = len(pages) > 1
        prompt = (
            "<image>Multi page parsing." if multi else "<image>document parsing."
        )
        allow_download = bool(local.get("allow_download"))

        try:
            import torch  # type: ignore
            from transformers import AutoModel, AutoTokenizer  # type: ignore
        except ImportError as exc:
            raise UnlimitedOCRError(
                "Local Unlimited-OCR requires transformers + torch"
            ) from exc

        device = local.get("device") or "auto"
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        try:
            tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                trust_remote_code=True,
                local_files_only=not allow_download,
            )
            model = AutoModel.from_pretrained(
                model_id,
                trust_remote_code=True,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                local_files_only=not allow_download,
            )
            model = model.eval().to(device)
        except Exception as exc:  # noqa: BLE001
            raise UnlimitedOCRError(
                f"Failed to load {model_id} "
                f"(local_files_only={not allow_download}): {exc}"
            ) from exc

        image_paths_or_pil = [p.image for p in pages]
        try:
            if multi and hasattr(model, "infer_multi"):
                text = str(
                    model.infer_multi(
                        tokenizer,
                        prompt=prompt,
                        images=image_paths_or_pil,
                        max_length=int(local.get("max_length") or 32768),
                        no_repeat_ngram_size=int(local.get("no_repeat_ngram_size") or 35),
                        ngram_window=int(local.get("ngram_window") or 1024),
                        save_results=False,
                    )
                    or ""
                )
            elif hasattr(model, "infer"):
                text = str(
                    model.infer(
                        tokenizer,
                        prompt=prompt if not multi else "<image>document parsing.",
                        image=image_paths_or_pil[0],
                        max_length=int(local.get("max_length") or 32768),
                        no_repeat_ngram_size=int(local.get("no_repeat_ngram_size") or 35),
                        ngram_window=int(local.get("ngram_window") or 128),
                        save_results=False,
                    )
                    or ""
                )
            else:
                raise UnlimitedOCRError("Loaded model has no infer/infer_multi hooks")
        except UnlimitedOCRError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise UnlimitedOCRError(f"Local infer failed: {exc}") from exc

        if not str(text).strip():
            raise UnlimitedOCRError("Local Unlimited-OCR returned empty text")

        chunks = _split_multi_page(str(text), len(pages))
        return [
            OCRPageResult(
                page_number=pages[i].page_number,
                raw_text=chunks[i],
                ocr_confidence=0.92,
            )
            for i in range(len(pages))
        ]

    # ---------------------------------------------------------------- Stub
    def _run_stub(self, pages: list[PageImage]) -> list[OCRPageResult]:
        from .preprocess import pages_to_text_stub

        results: list[OCRPageResult] = []
        fallback_texts = {p.page_number: p.metadata.get("stub_text") for p in pages}
        if any(fallback_texts.values()):
            for p in pages:
                text = str(fallback_texts.get(p.page_number) or "")
                if not text.strip():
                    raise UnlimitedOCRError("stub_text missing on a page")
                results.append(
                    OCRPageResult(
                        page_number=p.page_number,
                        raw_text=text,
                        ocr_confidence=0.75,
                    )
                )
            return results

        for page_no, text in pages_to_text_stub(pages):
            if not text.strip():
                raise UnlimitedOCRError(
                    "Stub OCR produced empty text (install Tesseract or inject stub_text)"
                )
            results.append(
                OCRPageResult(page_number=page_no, raw_text=text, ocr_confidence=0.7)
            )
        return results


def _extract_chat_text(data: dict[str, Any]) -> str:
    try:
        choices = data.get("choices") or []
        if not choices:
            return str(data.get("text") or data.get("output") or "")
        msg = choices[0].get("message") or {}
        content = msg.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    parts.append(c.get("text") or "")
                elif isinstance(c, str):
                    parts.append(c)
            return "\n".join(parts)
        return str(choices[0].get("text") or "")
    except Exception:  # noqa: BLE001
        return ""


def _split_multi_page(text: str, n_pages: int) -> list[str]:
    if n_pages <= 1:
        return [text]
    if "\f" in text:
        parts = text.split("\f")
    elif re_page_breaks(text):
        parts = re_page_breaks(text)
    else:
        parts = [text] + [""] * (n_pages - 1)
    while len(parts) < n_pages:
        parts.append("")
    return parts[:n_pages]


def re_page_breaks(text: str) -> list[str] | None:
    import re

    if re.search(r"(?i)page\s+\d+\s*[:\-]?", text):
        chunks = re.split(r"(?i)(?=page\s+\d+\s*[:\-]?)", text)
        chunks = [c for c in chunks if c.strip()]
        return chunks or None
    return None
