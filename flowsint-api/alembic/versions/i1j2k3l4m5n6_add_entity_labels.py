"""Add compliance_entity_labels for autonomous attribution."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "i1j2k3l4m5n6_entity_labels"
down_revision = "h0i1j2k3l4m5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_entity_labels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chain", sa.String(16), nullable=False),
        sa.Column("address", sa.String(128), nullable=False),
        sa.Column("label", sa.String(256), nullable=False),
        sa.Column("category", sa.String(64), server_default="unknown"),
        sa.Column("confidence", sa.Float(), server_default="0.5"),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("tier", sa.Integer(), server_default="2"),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("sanctioned", sa.Boolean(), server_default="false"),
        sa.Column("cluster_ref", sa.String(128), nullable=True),
        sa.Column("evidence", sa.String(512), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "idx_entity_labels_chain_address",
        "compliance_entity_labels",
        ["chain", "address"],
        unique=True,
    )
    op.create_index("idx_entity_labels_source", "compliance_entity_labels", ["source"])


def downgrade() -> None:
    op.drop_index("idx_entity_labels_source", table_name="compliance_entity_labels")
    op.drop_index("idx_entity_labels_chain_address", table_name="compliance_entity_labels")
    op.drop_table("compliance_entity_labels")
