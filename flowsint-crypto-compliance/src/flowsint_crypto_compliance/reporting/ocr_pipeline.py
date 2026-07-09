"""
OCR-пайплайн для документов изъятия активов.

Цепочка: PDF/изображение → текст (PyMuPDF / Tesseract) → извлечение сущностей
→ структурированные поля для отчёта об изъятии.

Вдохновлено: PaddleOCR, fin-doc-parser, docpick (опциональные бэкенды).
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from flowsint_crypto_compliance.osint_core.scalpel.entity_extractor import extract_entities

_SEIZURE_FIELD_PATTERNS: dict[str, re.Pattern[str]] = {
    "case_number": re.compile(
        r"(?:дело|производство|№)\s*(?:№\s*)?([А-Яа-я0-9\-/]{5,40})",
        re.I,
    ),
    "court": re.compile(
        r"(?:суд|арбитражный суд|районный суд)\s+([А-Яа-яё\s\-«»\"]{5,80})",
        re.I,
    ),
    "subject": re.compile(
        r"(?:ответчик|подозреваемый|лицо)[:\s]+([А-Яа-яё\s]{5,80})",
        re.I,
    ),
    "asset_type": re.compile(
        r"(?:криптовалют|цифров\w+\s+актив|USDT|BTC|ETH|TRON|биткоин)",
        re.I,
    ),
    "amount_rub": re.compile(
        r"(\d[\d\s.,]*)\s*(?:₽|руб\.?|RUB)",
        re.I,
    ),
    "wallet": re.compile(
        r"\b(T[1-9A-HJ-NP-Za-km-z]{33}|0x[a-fA-F0-9]{40}|(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62})\b",
    ),
}


@dataclass
class OCRDocumentResult:
    filename: str
    backend: str
    text_chars: int
    full_text: str
    entities: dict[str, Any] = field(default_factory=dict)
    seizure_fields: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)
    processed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "backend": self.backend,
            "text_chars": self.text_chars,
            "full_text_preview": self.full_text[:4000],
            "full_text": self.full_text,
            "entities": self.entities,
            "seizure_fields": self.seizure_fields,
            "confidence": round(self.confidence, 3),
            "warnings": self.warnings,
            "processed_at": self.processed_at or _now(),
            "suitable_for_seizure_report": bool(
                self.seizure_fields.get("wallets") or self.entities.get("crypto_addresses")
            ),
        }


class OCRPipeline:
    """Извлечение текста и полей из сканов/ PDF для изъятия активов."""

    def process_bytes(
        self,
        data: bytes,
        filename: str,
        *,
        backend: str = "auto",
    ) -> OCRDocumentResult:
        warnings: list[str] = []
        text, used_backend = self._extract_text(data, filename, backend, warnings)
        entities = extract_entities(text).to_dict()
        seizure = _extract_seizure_fields(text)
        if entities.get("crypto_addresses"):
            seizure["wallets"] = entities["crypto_addresses"]
        conf = _ocr_confidence(text, used_backend)

        return OCRDocumentResult(
            filename=filename,
            backend=used_backend,
            text_chars=len(text),
            full_text=text,
            entities=entities,
            seizure_fields=seizure,
            confidence=conf,
            warnings=warnings,
            processed_at=_now(),
        )

    def process_bytes_paddle(
        self,
        data: bytes,
        filename: str,
    ) -> OCRDocumentResult:
        return self.process_bytes(data, filename, backend="paddle")

    def process_file(self, path: str | Path, *, backend: str = "auto") -> OCRDocumentResult:
        p = Path(path)
        return self.process_bytes(p.read_bytes(), p.name, backend=backend)

    def _extract_text(
        self,
        data: bytes,
        filename: str,
        backend: str,
        warnings: list[str],
    ) -> tuple[str, str]:
        low = filename.lower()
        if backend in ("auto", "paddle") and _paddle_available():
            text, ok = _ocr_paddle(data, filename, warnings)
            if ok and len(text.strip()) > 10:
                return text, "paddleocr"
        if backend in ("auto", "pymupdf", "paddle") and low.endswith(".pdf"):
            text, ok = _pdf_text_pymupdf(data, warnings)
            if ok and len(text.strip()) > 40:
                return text, "pymupdf"
            if backend in ("auto", "paddle") and _paddle_available():
                text, ok = _pdf_ocr_paddle(data, warnings)
                if ok:
                    return text, "paddleocr_pdf"
        if backend in ("auto", "tesseract", "paddle") and low.endswith(
            (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp")
        ):
            if backend != "tesseract" and _paddle_available():
                text, ok = _ocr_paddle_image(data, warnings)
                if ok:
                    return text, "paddleocr"
            text, ok = _ocr_tesseract(data, warnings)
            if ok:
                return text, "tesseract"
        if backend == "paddle" and _paddle_available():
            text, ok = _ocr_paddle(data, filename, warnings)
            if ok:
                return text, "paddleocr"
        if low.endswith(".txt"):
            return data.decode("utf-8", errors="replace"), "plain_text"
        text, ok = _pdf_text_pymupdf(data, warnings)
        if ok and text.strip():
            return text, "pymupdf"
        warnings.append("fallback:utf8_decode")
        return data.decode("utf-8", errors="replace")[:100_000], "raw_decode"


def _extract_seizure_fields(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, pat in _SEIZURE_FIELD_PATTERNS.items():
        m = pat.search(text)
        if not m:
            continue
        if key == "wallet":
            out.setdefault("wallets", []).append({"address": m.group(0)})
        elif key == "amount_rub":
            out.setdefault("amounts_rub", []).append(m.group(1).strip())
        else:
            out[key] = m.group(1).strip() if m.lastindex else m.group(0)
    wallets = _SEIZURE_FIELD_PATTERNS["wallet"].findall(text)
    if wallets:
        out["wallets"] = [{"address": w} for w in dict.fromkeys(wallets)]
    return out


def _pdf_text_pymupdf(data: bytes, warnings: list[str]) -> tuple[str, bool]:
    try:
        import fitz  # pymupdf

        doc = fitz.open(stream=data, filetype="pdf")
        parts = [page.get_text() for page in doc]
        doc.close()
        return "\n".join(parts), True
    except ImportError:
        warnings.append("pymupdf_not_installed: pip install pymupdf")
        return "", False
    except Exception as exc:
        warnings.append(f"pymupdf_error:{exc.__class__.__name__}")
        return "", False


def _ocr_tesseract(data: bytes, warnings: list[str]) -> tuple[str, bool]:
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(io.BytesIO(data))
        text = pytesseract.image_to_string(img, lang="rus+eng")
        return text, len(text.strip()) > 10
    except ImportError:
        warnings.append("tesseract_not_installed: pip install pytesseract pillow + system tesseract")
        return "", False
    except Exception as exc:
        warnings.append(f"tesseract_error:{exc.__class__.__name__}")
        return "", False


def _ocr_confidence(text: str, backend: str) -> float:
    if not text.strip():
        return 0.0
    base = {
        "pymupdf": 0.92,
        "paddleocr": 0.88,
        "paddleocr_pdf": 0.86,
        "tesseract": 0.78,
        "plain_text": 0.99,
        "raw_decode": 0.35,
    }.get(backend, 0.5)
    if len(text) > 500:
        base = min(0.98, base + 0.05)
    return base


def _paddle_available() -> bool:
    try:
        import paddleocr  # noqa: F401

        return True
    except ImportError:
        return False


def _get_paddle_ocr() -> Any:
    from paddleocr import PaddleOCR

    lang = __import__("os").getenv("FINSKALP_PADDLE_LANG", "ru")
    return PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)


def _ocr_paddle_image(data: bytes, warnings: list[str]) -> tuple[str, bool]:
    try:
        import numpy as np
        from PIL import Image

        img = Image.open(io.BytesIO(data)).convert("RGB")
        arr = np.array(img)
        ocr = _get_paddle_ocr()
        result = ocr.ocr(arr, cls=True)
        lines = _paddle_lines(result)
        return "\n".join(lines), len(lines) > 0
    except ImportError:
        warnings.append("paddleocr_not_installed: uv sync --extra paddleocr")
        return "", False
    except Exception as exc:
        warnings.append(f"paddleocr_error:{exc.__class__.__name__}")
        return "", False


def _ocr_paddle(data: bytes, filename: str, warnings: list[str]) -> tuple[str, bool]:
    low = filename.lower()
    if low.endswith(".pdf"):
        return _pdf_ocr_paddle(data, warnings)
    return _ocr_paddle_image(data, warnings)


def _pdf_ocr_paddle(data: bytes, warnings: list[str]) -> tuple[str, bool]:
    try:
        import fitz
        import numpy as np

        ocr = _get_paddle_ocr()
        doc = fitz.open(stream=data, filetype="pdf")
        parts: list[str] = []
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:
                arr = arr[:, :, :3]
            result = ocr.ocr(arr, cls=True)
            parts.extend(_paddle_lines(result))
        doc.close()
        text = "\n".join(parts)
        return text, len(text.strip()) > 20
    except ImportError as exc:
        warnings.append(f"paddle_pdf_deps:{exc}")
        return "", False
    except Exception as exc:
        warnings.append(f"paddle_pdf_error:{exc.__class__.__name__}")
        return "", False


def _paddle_lines(result: Any) -> list[str]:
    lines: list[str] = []
    if not result:
        return lines
    for block in result:
        if not block:
            continue
        for line in block:
            if line and len(line) >= 2 and line[1]:
                text = line[1][0] if isinstance(line[1], (list, tuple)) else str(line[1])
                if text:
                    lines.append(str(text))
    return lines


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
