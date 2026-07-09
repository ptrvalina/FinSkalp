"""RFC-0014 Ch.11 — image processing."""

from __future__ import annotations

from typing import Any

from flowsint_crypto_compliance.platform.v2.icf.entity_extractor import get_entity_extractor


class ImageProcessor:
    """OCR / QR / barcode stubs with structured output."""

    def process(
        self,
        *,
        filename: str = "image.png",
        mime_type: str = "image/png",
        content_hint: str = "",
        connector_id: str = "image",
        provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ocr_text = self._ocr_stub(content_hint, mime_type)
        qr_codes = self._qr_stub(filename)
        barcodes = self._barcode_stub(filename)
        doc_type = self._detect_document_type(mime_type, filename)
        entities = get_entity_extractor().extract_from_records(
            [{"entity_type": "document", "entity_value": ocr_text[:256], "payload": {"ocr": ocr_text}}],
            connector_id=connector_id,
            provenance_base=provenance,
        )
        requisites = []
        if "ИНН" in ocr_text or "р/с" in ocr_text:
            requisites.append({"type": "bank_requisite", "stub": True})
        return {
            "filename": filename,
            "mime_type": mime_type,
            "document_type": doc_type,
            "ocr_text": ocr_text,
            "qr_codes": qr_codes,
            "barcodes": barcodes,
            "requisites": requisites,
            "entities": entities,
            "evidence_ready": True,
        }

    @staticmethod
    def _ocr_stub(hint: str, mime_type: str) -> str:
        if hint:
            return hint
        return f"[OCR stub for {mime_type}]"

    @staticmethod
    def _qr_stub(filename: str) -> list[dict[str, Any]]:
        if "qr" in filename.lower():
            return [{"format": "QR", "payload": "stub://qr", "stub": True}]
        return []

    @staticmethod
    def _barcode_stub(filename: str) -> list[dict[str, Any]]:
        if "barcode" in filename.lower() or "ean" in filename.lower():
            return [{"format": "EAN13", "payload": "stub-barcode", "stub": True}]
        return []

    @staticmethod
    def _detect_document_type(mime_type: str, filename: str) -> str:
        if "scan" in filename.lower():
            return "scanned_document"
        if mime_type == "image/tiff":
            return "tiff_scan"
        return "image"


_processor: ImageProcessor | None = None


def get_image_processor() -> ImageProcessor:
    global _processor
    if _processor is None:
        _processor = ImageProcessor()
    return _processor
