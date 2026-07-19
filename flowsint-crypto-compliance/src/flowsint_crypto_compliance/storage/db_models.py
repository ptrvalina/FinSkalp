from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from flowsint_core.core.models import Base


class ComplianceCase(Base):
    """Regulator compliance investigation case."""

    __tablename__ = "compliance_cases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_ref: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    investigation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    status: Mapped[str] = mapped_column(String(32), server_default="draft")
    workflow_status: Mapped[str] = mapped_column(String(32), server_default="new")
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    priority: Mapped[str] = mapped_column(String(16), server_default="normal")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sla_breached: Mapped[bool] = mapped_column(Boolean, server_default="false")
    queue_priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fusion_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ComplianceCaseComment(Base):
    __tablename__ = "compliance_case_comments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())


class ComplianceUserRole(Base):
    __tablename__ = "compliance_user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, server_default="analyst")
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ComplianceBatchScreenJob(Base):
    __tablename__ = "compliance_batch_screen_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), server_default="pending")
    total: Mapped[int] = mapped_column(Integer, server_default="0")
    processed: Mapped[int] = mapped_column(Integer, server_default="0")
    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    results: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ComplianceWatchlistSubscription(Base):
    __tablename__ = "compliance_watchlist_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(128), nullable=False)
    chain: Mapped[str] = mapped_column(String(16), server_default="tron")
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_hit_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_watchlist_owner_address", "owner_id", "address", "chain", unique=True),
    )


class ComplianceWebhookEndpoint(Base):
    __tablename__ = "compliance_webhook_endpoints"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    bank_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    secret_hint: Mapped[str] = mapped_column(String(16), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default="true")
    outbound_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())


class ComplianceBankFeed(Base):
    """Ingested bank feed row linked to a compliance case."""

    __tablename__ = "compliance_bank_feeds"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True
    )
    feed_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    ingested_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_compliance_bank_feeds_case_feed", "case_id", "feed_id", unique=True),
    )


class ComplianceRegistryLabel(Base):
    """Sovereign RF/CIS risk-label registry entry stored for fusion lookups."""

    __tablename__ = "compliance_registry_labels"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    chain: Mapped[str] = mapped_column(String(16), nullable=False)
    address: Mapped[str] = mapped_column(String(128), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, server_default="0.5")
    sanctioned: Mapped[bool] = mapped_column(Boolean, server_default="false")
    list_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    disputed: Mapped[bool] = mapped_column(Boolean, server_default="false")
    snapshot_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cluster_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    label_id: Mapped[str] = mapped_column(String(256), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_compliance_registry_chain_address", "chain", "address", unique=True),
        Index("idx_compliance_registry_source", "source"),
    )


class ComplianceEntityLabel(Base):
    """Accumulative autonomous attribution labels (FinSkalp entity_labels)."""

    __tablename__ = "compliance_entity_labels"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    chain: Mapped[str] = mapped_column(String(16), nullable=False)
    address: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    category: Mapped[str] = mapped_column(String(64), server_default="unknown")
    confidence: Mapped[float] = mapped_column(Float, server_default="0.5")
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    tier: Mapped[int] = mapped_column(Integer, server_default="2")
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sanctioned: Mapped[bool] = mapped_column(Boolean, server_default="false")
    cluster_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    evidence: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(16), server_default="active")
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    added_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_entity_labels_chain_address", "chain", "address", unique=True),
        Index("idx_entity_labels_source", "source"),
    )


class ComplianceAttributionSyncState(Base):
    """Tracks last open-dataset bootstrap to avoid full reload on service restart."""

    __tablename__ = "compliance_attribution_sync_state"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    sync_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    last_sync_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    stats_json: Mapped[str | None] = mapped_column(String(8192), nullable=True)


class ComplianceFusionRun(Base):
    """Async or sync OSINT fusion execution record."""

    __tablename__ = "compliance_fusion_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), server_default="pending")
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())


class ComplianceAuditLog(Base):
    """Append-only audit trail for compliance analyst actions."""

    __tablename__ = "compliance_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())


class ComplianceReadSnapshot(Base):
    """CQRS read-model snapshot (denormalized dashboard / registry views)."""

    __tablename__ = "compliance_read_snapshots"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class OsintSourceReliability(Base):
    __tablename__ = "osint_source_reliability"

    source_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    historical_precision: Mapped[float] = mapped_column(Float, server_default="0.55")
    sample_size: Mapped[int] = mapped_column(Integer, server_default="0")
    last_updated = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class OsintFinding(Base):
    __tablename__ = "osint_findings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    case_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_value: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, server_default="0.5")
    payload: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    discovered_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_osint_findings_tenant_entity", "tenant_id", "entity_type", "entity_value"),
        Index("uq_osint_findings_tenant_entity_case", "tenant_id", "entity_type", "entity_value", "case_id", unique=True),
    )


class ComplianceGraphView(Base):
    """Analyst-saved graph camera state for an investigation."""

    __tablename__ = "compliance_graph_views"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    zoom: Mapped[float] = mapped_column(Float, server_default="1.0")
    center: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    expanded_clusters: Mapped[list] = mapped_column(JSONB, server_default="[]")
    timeline_ts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pins: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    view_mode: Mapped[str] = mapped_column(String(16), server_default="cluster")
    highlighted_path: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("uq_graph_view_inv_name", "investigation_id", "name", unique=True),
    )


class FinskalpEntity(Base):
    """RFC-0002 canonical Entity — Knowledge Layer."""

    __tablename__ = "finskalp_entities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    canonical_key: Mapped[str] = mapped_column(String(512), nullable=False)
    display_name: Mapped[str] = mapped_column(String(512), server_default="")
    version: Mapped[int] = mapped_column(Integer, server_default="1")
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("uq_finskalp_entity_tenant_type_key", "tenant_id", "entity_type", "canonical_key", unique=True),
    )


class FinskalpEntityAttribute(Base):
    __tablename__ = "finskalp_entity_attributes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    source: Mapped[str] = mapped_column(String(64), server_default="unknown")
    confidence: Mapped[float] = mapped_column(Float, server_default="0.5")
    valid_from = mapped_column(DateTime(timezone=True), server_default=func.now())


class FinskalpEntityRelation(Base):
    __tablename__ = "finskalp_entity_relations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    from_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    to_entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, server_default="0.5")
    evidence_ids: Mapped[list] = mapped_column(JSONB, server_default="[]")
    source: Mapped[str] = mapped_column(String(64), server_default="unknown")
    acquisition_method: Mapped[str] = mapped_column(String(64), server_default="inferred")
    actor: Mapped[str] = mapped_column(String(128), server_default="system")
    valid_until = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, server_default="1")
    history: Mapped[list] = mapped_column(JSONB, server_default="[]")
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())


class FinskalpEvidence(Base):
    """RFC-0002 Evidence Center, RFC-0003 extensions."""

    __tablename__ = "finskalp_evidence"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    case_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    snapshot_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    trust_level: Mapped[float] = mapped_column(Float, server_default="0.5")
    payload: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    discovered_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    acquisition_method: Mapped[str] = mapped_column(String(64), server_default="automated_collection")
    digital_signature: Mapped[str | None] = mapped_column(String(256), nullable=True)
    original_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    retention_policy: Mapped[str] = mapped_column(String(64), server_default="standard_7y")
    valid_until = mapped_column(DateTime(timezone=True), nullable=True)


class FinskalpEntityVersion(Base):
    """RFC-0003 entity version history."""

    __tablename__ = "finskalp_entity_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    changed_by: Mapped[str] = mapped_column(String(128), server_default="system")
    changed_at = mapped_column(DateTime(timezone=True), server_default=func.now())


class FinskalpRelationVersion(Base):
    """RFC-0003 relation version history."""

    __tablename__ = "finskalp_relation_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    relation_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    changed_by: Mapped[str] = mapped_column(String(128), server_default="system")
    changed_at = mapped_column(DateTime(timezone=True), server_default=func.now())


class FinskalpGraphSnapshot(Base):
    """RFC-0003 point-in-time graph snapshots."""

    __tablename__ = "finskalp_graph_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    as_of = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    snapshot: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())


class FinskalpPlatformEvent(Base):
    """Append-only platform event log — RFC-0002 event store."""

    __tablename__ = "finskalp_platform_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String(16), server_default="2.0.0")
    occurred_at = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), server_default="system")
    investigation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, server_default="{}")


class FinskalpBlockSyncCursor(Base):
    """RFC-0013 per-chain incremental sync cursor."""

    __tablename__ = "finskalp_block_sync_cursors"

    chain: Mapped[str] = mapped_column(String(32), primary_key=True)
    last_block_height: Mapped[int] = mapped_column(Integer, server_default="0")
    last_block_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    blocks_processed: Mapped[int] = mapped_column(Integer, server_default="0")
    transactions_processed: Mapped[int] = mapped_column(Integer, server_default="0")
    error_count: Mapped[int] = mapped_column(Integer, server_default="0")
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FinskalpChainBlock(Base):
    """RFC-0013 canonical block records."""

    __tablename__ = "finskalp_chain_blocks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    chain: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    block_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    tx_count: Mapped[int] = mapped_column(Integer, server_default="0")
    block_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("uq_finskalp_chain_block", "chain", "height", unique=True),
    )


class FinskalpIndexedTransfer(Base):
    """RFC-0013 address→transfer index for local analyze."""

    __tablename__ = "finskalp_indexed_transfers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    chain: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    address_key: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    tx_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_address: Mapped[str] = mapped_column(String(256), server_default="")
    target_address: Mapped[str] = mapped_column(String(256), server_default="")
    asset: Mapped[str | None] = mapped_column(String(32), nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    block_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    indexed_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_finskalp_indexed_transfer_chain_addr", "chain", "address_key"),
    )


class FinskalpSyncLock(Base):
    """RFC-0013 distributed sync lock."""

    __tablename__ = "finskalp_sync_locks"

    lock_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    holder_id: Mapped[str] = mapped_column(String(128), nullable=False)
    acquired_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at = mapped_column(DateTime(timezone=True), nullable=False)


class EccfEvidenceRecord(Base):
    """RFC-0017 ECCF evidence — append-only content, metadata lifecycle updates only."""

    __tablename__ = "eccf_evidence_records"

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, server_default="1")
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    lifecycle: Mapped[str] = mapped_column(String(32), server_default="registered")
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_value: Mapped[str] = mapped_column(String(512), nullable=False)
    case_ref: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    kg_evidence_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    provenance: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    prior_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    immutable: Mapped[bool] = mapped_column(Boolean, server_default="true")
    archived: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("uq_eccf_evidence_tenant_hash", "tenant_id", "content_hash", unique=True),
        Index("ix_eccf_evidence_content_hash", "content_hash"),
    )


class EccfAuditLogEntry(Base):
    """RFC-0017 append-only audit trail with tamper-evident hash chain."""

    __tablename__ = "eccf_audit_log"

    entry_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evidence_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    timestamp = mapped_column(DateTime(timezone=True), server_default=func.now())
    details: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    __table_args__ = (
        Index("ix_eccf_audit_evidence_ts", "evidence_id", "timestamp"),
    )


class EsaSecurityAuditEntry(Base):
    """RFC-0020 append-only security audit (Wave 5 Postgres persistence)."""

    __tablename__ = "esa_security_audit"

    entry_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource: Mapped[str] = mapped_column(String(256), server_default="", nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), server_default="success", nullable=False)
    timestamp = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    details: Mapped[dict] = mapped_column(JSONB, server_default="{}")
