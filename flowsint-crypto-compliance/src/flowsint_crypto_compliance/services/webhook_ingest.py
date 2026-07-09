"""Inbound bank webhook verification and STR ingest."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from typing import Any

from sqlalchemy.orm import Session

from flowsint_crypto_compliance.schemas.hub import validate_bank_feed_batch
from flowsint_crypto_compliance.services.compliance_service import ComplianceService
from flowsint_crypto_compliance.storage.db_models import ComplianceWebhookEndpoint


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    sig = signature.removeprefix("sha256=").strip()
    return hmac.compare_digest(expected, sig)


def resolve_webhook_secret(db: Session, bank_id: str) -> str | None:
    row = db.query(ComplianceWebhookEndpoint).filter(ComplianceWebhookEndpoint.bank_id == bank_id).first()
    if row and not row.enabled:
        return None
    env_key = f"COMPLIANCE_WEBHOOK_SECRET_{bank_id.upper().replace('-', '_')}"
    secret = os.getenv(env_key) or os.getenv("COMPLIANCE_WEBHOOK_SECRET")
    if secret:
        return secret
    from flowsint_crypto_compliance.secrets.compliance_secrets import get_compliance_secret

    return get_compliance_secret(f"webhook:{bank_id}")


class WebhookIngestService:
    def __init__(self, db: Session):
        self._db = db
        self._compliance = ComplianceService(db)

    def register_endpoint(self, bank_id: str, secret: str, outbound_url: str | None = None) -> ComplianceWebhookEndpoint:
        hint = secret[:4] + "…" + secret[-2:] if len(secret) > 8 else "****"
        row = self._db.query(ComplianceWebhookEndpoint).filter(ComplianceWebhookEndpoint.bank_id == bank_id).first()
        if row:
            row.secret_hint = hint
            row.outbound_url = outbound_url
            row.enabled = True
        else:
            row = ComplianceWebhookEndpoint(bank_id=bank_id, secret_hint=hint, outbound_url=outbound_url)
            self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        os.environ[f"COMPLIANCE_WEBHOOK_SECRET_{bank_id.upper().replace('-', '_')}"] = secret
        return row

    def ingest(
        self,
        *,
        bank_id: str,
        payload: dict[str, Any],
        case_id: uuid.UUID,
        idempotency_key: str | None = None,
    ) -> int:
        from flowsint_crypto_compliance.infrastructure.idempotency import IdempotencyStore

        if idempotency_key:
            store = IdempotencyStore()
            if store.acquire("webhook_ingest", idempotency_key) == "done":
                cached = store.get_result("webhook_ingest", idempotency_key)
                if cached is not None:
                    return int(cached.get("ingested", 0))

        validate_bank_feed_batch(payload)
        count = self._compliance.ingest_bank_feed_batch(case_id, payload)
        self._compliance.log_audit(
            case_id=case_id,
            action="bank_webhook_ingested",
            payload={"bank_id": bank_id, "count": count, "idempotency_key": idempotency_key},
        )
        self._db.commit()
        if idempotency_key:
            IdempotencyStore().complete("webhook_ingest", idempotency_key, {"ingested": count})
        return count

    @staticmethod
    def parse_body(raw: bytes) -> dict[str, Any]:
        return json.loads(raw.decode("utf-8"))
