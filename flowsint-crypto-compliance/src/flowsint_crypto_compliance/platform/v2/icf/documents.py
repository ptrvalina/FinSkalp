"""RFC-0014 Ch.10 — document processing."""

from __future__ import annotations

import re
from typing import Any

from flowsint_crypto_compliance.platform.v2.icf.entity_extractor import get_entity_extractor


class DocumentProcessor:
    """OCR / text / table / requisite stubs with structured output."""

    def process(
        self,
        content: str | bytes,
        *,
        mime_type: str = "text/plain",
        connector_id: str = "document",
        provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        text = content.decode("utf-8", errors="ignore") if isinstance(content, bytes) else content
        tables = self._extract_tables_stub(text)
        requisites = self._extract_requisites_stub(text)
        ocr_text = self._ocr_stub(text, mime_type)
        entities = get_entity_extractor().extract_from_records(
            [{"entity_type": "document", "entity_value": text[:256], "payload": {"text": text[:2000]}}],
            connector_id=connector_id,
            provenance_base=provenance,
        )
        return {
            "mime_type": mime_type,
            "ocr_text": ocr_text,
            "text_length": len(text),
            "tables": tables,
            "requisites": requisites,
            "classification": self._classify_stub(mime_type),
            "entities": entities,
            "evidence_ready": True,
        }

    @staticmethod
    def _ocr_stub(text: str, mime_type: str) -> str:
        if mime_type in ("application/pdf", "image/png", "image/jpeg", "image/tiff"):
            return f"[OCR stub] {text[:500]}"
        return text

    @staticmethod
    def _extract_tables_stub(text: str) -> list[dict[str, Any]]:
        rows = [line.split() for line in text.splitlines() if "\t" in line or "|" in line]
        return [{"row_count": len(rows), "stub": True}] if rows else []

    @staticmethod
    def _extract_requisites_stub(text: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in re.finditer(r"\b(?:ИНН|ОГРН|БИК|р/с|к/с)[:\s]*[\d\s/\-]+", text, re.I):
            out.append({"type": "requisite", "value": m.group(0).strip(), "stub": True})
        return out[:10]

    @staticmethod
    def _classify_stub(mime_type: str) -> str:
        mapping = {
            "application/pdf": "pdf_document",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
            "text/csv": "csv",
            "application/xml": "xml",
            "application/json": "json",
        }
        return mapping.get(mime_type, "unknown_document")


_processor: DocumentProcessor | None = None


def get_document_processor() -> DocumentProcessor:
    global _processor
    if _processor is None:
        _processor = DocumentProcessor()
    return _processor
