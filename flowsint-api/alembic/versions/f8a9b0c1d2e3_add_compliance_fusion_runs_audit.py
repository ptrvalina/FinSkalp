"""add compliance fusion runs and audit log tables

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-07-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "compliance_fusion_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("celery_task_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.String(length=2048), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_compliance_fusion_runs_case_id", "compliance_fusion_runs", ["case_id"])
    op.create_index(
        "idx_compliance_fusion_runs_celery_task_id",
        "compliance_fusion_runs",
        ["celery_task_id"],
    )

    op.create_table(
        "compliance_audit_log",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=True),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_compliance_audit_log_case_id", "compliance_audit_log", ["case_id"])


def downgrade() -> None:
    op.drop_index("idx_compliance_audit_log_case_id", table_name="compliance_audit_log")
    op.drop_table("compliance_audit_log")
    op.drop_index("idx_compliance_fusion_runs_celery_task_id", table_name="compliance_fusion_runs")
    op.drop_index("idx_compliance_fusion_runs_case_id", table_name="compliance_fusion_runs")
    op.drop_table("compliance_fusion_runs")
