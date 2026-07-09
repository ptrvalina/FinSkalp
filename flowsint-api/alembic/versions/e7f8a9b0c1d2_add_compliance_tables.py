"""add compliance cases, bank feeds and sovereign registry label tables

Revision ID: e7f8a9b0c1d2
Revises: a1f2b3c4d5e6
Create Date: 2026-06-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, None] = "a1f2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "compliance_cases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("case_ref", sa.String(length=128), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("investigation_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("fusion_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_ref"),
    )
    op.create_index("idx_compliance_cases_owner_id", "compliance_cases", ["owner_id"])

    op.create_table(
        "compliance_bank_feeds",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("feed_id", sa.String(length=128), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_compliance_bank_feeds_case_id", "compliance_bank_feeds", ["case_id"])
    op.create_index(
        "idx_compliance_bank_feeds_case_feed",
        "compliance_bank_feeds",
        ["case_id", "feed_id"],
        unique=True,
    )

    op.create_table(
        "compliance_registry_labels",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("chain", sa.String(length=16), nullable=False),
        sa.Column("address", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("entity_name", sa.String(length=256), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("sanctioned", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("list_reference", sa.String(length=128), nullable=True),
        sa.Column("disputed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("snapshot_at", sa.String(length=64), nullable=True),
        sa.Column("cluster_ref", sa.String(length=128), nullable=True),
        sa.Column("label_id", sa.String(length=256), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_compliance_registry_chain_address",
        "compliance_registry_labels",
        ["chain", "address"],
        unique=True,
    )
    op.create_index("idx_compliance_registry_source", "compliance_registry_labels", ["source"])


def downgrade() -> None:
    op.drop_index("idx_compliance_registry_source", table_name="compliance_registry_labels")
    op.drop_index("idx_compliance_registry_chain_address", table_name="compliance_registry_labels")
    op.drop_table("compliance_registry_labels")
    op.drop_index("idx_compliance_bank_feeds_case_feed", table_name="compliance_bank_feeds")
    op.drop_index("idx_compliance_bank_feeds_case_id", table_name="compliance_bank_feeds")
    op.drop_table("compliance_bank_feeds")
    op.drop_index("idx_compliance_cases_owner_id", table_name="compliance_cases")
    op.drop_table("compliance_cases")
