"""osint_source_reliability + osint_findings tables for FinSkalp OSINT quality."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m5n6o7p8q9r0"
down_revision: Union[str, None] = "l4m5n6o7p8q9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "osint_source_reliability",
        sa.Column("source_name", sa.String(length=128), nullable=False),
        sa.Column("historical_precision", sa.Float(), server_default="0.55", nullable=False),
        sa.Column("sample_size", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("source_name"),
    )

    op.create_table(
        "osint_findings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("case_ref", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_value", sa.String(length=512), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["case_id"], ["compliance_cases.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_osint_findings_tenant_entity", "osint_findings", ["tenant_id", "entity_type", "entity_value"])
    op.create_index("idx_osint_findings_case", "osint_findings", ["case_id"])
    op.create_index(
        "uq_osint_findings_tenant_entity_case",
        "osint_findings",
        ["tenant_id", "entity_type", "entity_value", "case_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_osint_findings_tenant_entity_case", table_name="osint_findings")
    op.drop_index("idx_osint_findings_case", table_name="osint_findings")
    op.drop_index("idx_osint_findings_tenant_entity", table_name="osint_findings")
    op.drop_table("osint_findings")
    op.drop_table("osint_source_reliability")
