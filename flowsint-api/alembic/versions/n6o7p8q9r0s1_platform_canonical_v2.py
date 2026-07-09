"""RFC-0002 canonical platform tables — Knowledge Layer + event store."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "n6o7p8q9r0s1"
down_revision: Union[str, None] = "m5n6o7p8q9r0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "finskalp_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("canonical_key", sa.String(512), nullable=False),
        sa.Column("display_name", sa.String(512), server_default="", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_finskalp_entities_tenant_id", "finskalp_entities", ["tenant_id"])
    op.create_index("ix_finskalp_entities_entity_type", "finskalp_entities", ["entity_type"])
    op.create_index(
        "uq_finskalp_entity_tenant_type_key",
        "finskalp_entities",
        ["tenant_id", "entity_type", "canonical_key"],
        unique=True,
    )

    op.create_table(
        "finskalp_entity_attributes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("value", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("source", sa.String(64), server_default="unknown", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_finskalp_entity_attributes_entity_id", "finskalp_entity_attributes", ["entity_id"])

    op.create_table(
        "finskalp_entity_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation_type", sa.String(64), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_finskalp_entity_relations_tenant_id", "finskalp_entity_relations", ["tenant_id"])
    op.create_index("ix_finskalp_entity_relations_from", "finskalp_entity_relations", ["from_entity_id"])
    op.create_index("ix_finskalp_entity_relations_to", "finskalp_entity_relations", ["to_entity_id"])

    op.create_table(
        "finskalp_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("content_hash", sa.String(128), nullable=False),
        sa.Column("snapshot_uri", sa.Text(), nullable=True),
        sa.Column("trust_level", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_finskalp_evidence_tenant_id", "finskalp_evidence", ["tenant_id"])
    op.create_index("ix_finskalp_evidence_content_hash", "finskalp_evidence", ["content_hash"])
    op.create_index("ix_finskalp_evidence_case_id", "finskalp_evidence", ["case_id"])

    op.create_table(
        "finskalp_platform_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("schema_version", sa.String(16), server_default="2.0.0", nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(128), server_default="system", nullable=False),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("payload", postgresql.JSONB(), server_default="{}", nullable=False),
    )
    op.create_index("ix_finskalp_platform_events_event_type", "finskalp_platform_events", ["event_type"])
    op.create_index("ix_finskalp_platform_events_occurred_at", "finskalp_platform_events", ["occurred_at"])
    op.create_index("ix_finskalp_platform_events_investigation_id", "finskalp_platform_events", ["investigation_id"])


def downgrade() -> None:
    op.drop_table("finskalp_platform_events")
    op.drop_table("finskalp_evidence")
    op.drop_table("finskalp_entity_relations")
    op.drop_table("finskalp_entity_attributes")
    op.drop_table("finskalp_entities")
