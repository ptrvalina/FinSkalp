"""Analyst saved graph views per investigation."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "k3l4m5n6o7p8_graph_views"
down_revision = "j2k3l4m5n6o7_entity_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_graph_views",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("zoom", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("center", postgresql.JSONB(), nullable=True),
        sa.Column("expanded_clusters", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("timeline_ts", sa.Integer(), nullable=True),
        sa.Column("pins", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("view_mode", sa.String(16), server_default="cluster", nullable=False),
        sa.Column("highlighted_path", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("investigation_id", "name", name="uq_graph_view_inv_name"),
    )


def downgrade() -> None:
    op.drop_table("compliance_graph_views")
