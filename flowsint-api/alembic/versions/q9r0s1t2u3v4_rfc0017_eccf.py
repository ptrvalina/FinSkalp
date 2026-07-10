"""RFC-0017 ECCF Postgres persistence — eccf_evidence_records + eccf_audit_log."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "q9r0s1t2u3v4_rfc0017_eccf"
down_revision: Union[str, None] = "p8q9r0s1t2u3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "eccf_evidence_records",
        sa.Column("evidence_id", sa.String(64), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("content_hash", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("lifecycle", sa.String(32), server_default="registered", nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_value", sa.String(512), nullable=False),
        sa.Column("case_ref", sa.String(128), nullable=True),
        sa.Column("kg_evidence_id", sa.String(64), nullable=True),
        sa.Column("payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("provenance", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("prior_version_id", sa.String(64), nullable=True),
        sa.Column("immutable", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("archived", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_eccf_evidence_records_tenant_id", "eccf_evidence_records", ["tenant_id"])
    op.create_index("ix_eccf_evidence_records_case_ref", "eccf_evidence_records", ["case_ref"])
    op.create_index("ix_eccf_evidence_content_hash", "eccf_evidence_records", ["content_hash"])
    op.create_index(
        "uq_eccf_evidence_tenant_hash",
        "eccf_evidence_records",
        ["tenant_id", "content_hash"],
        unique=True,
    )

    op.create_table(
        "eccf_audit_log",
        sa.Column("entry_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("evidence_id", sa.String(64), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("details", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("prev_hash", sa.String(64), nullable=False),
        sa.Column("entry_hash", sa.String(64), nullable=False),
    )
    op.create_index("ix_eccf_audit_log_evidence_id", "eccf_audit_log", ["evidence_id"])
    op.create_index("ix_eccf_audit_log_entry_hash", "eccf_audit_log", ["entry_hash"])
    op.create_index("ix_eccf_audit_evidence_ts", "eccf_audit_log", ["evidence_id", "timestamp"])


def downgrade() -> None:
    op.drop_index("ix_eccf_audit_evidence_ts", table_name="eccf_audit_log")
    op.drop_index("ix_eccf_audit_log_entry_hash", table_name="eccf_audit_log")
    op.drop_index("ix_eccf_audit_log_evidence_id", table_name="eccf_audit_log")
    op.drop_table("eccf_audit_log")
    op.drop_index("uq_eccf_evidence_tenant_hash", table_name="eccf_evidence_records")
    op.drop_index("ix_eccf_evidence_content_hash", table_name="eccf_evidence_records")
    op.drop_index("ix_eccf_evidence_records_case_ref", table_name="eccf_evidence_records")
    op.drop_index("ix_eccf_evidence_records_tenant_id", table_name="eccf_evidence_records")
    op.drop_table("eccf_evidence_records")
