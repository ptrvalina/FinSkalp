"""Entity label review columns + attribution sync state."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "j2k3l4m5n6o7_entity_review"
down_revision = "i1j2k3l4m5n6_entity_labels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "compliance_entity_labels",
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
    )
    op.add_column(
        "compliance_entity_labels",
        sa.Column("reviewed_by", sa.String(128), nullable=True),
    )
    op.add_column(
        "compliance_entity_labels",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "compliance_attribution_sync_state",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sync_key", sa.String(64), nullable=False, unique=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("stats_json", sa.String(8192), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("compliance_attribution_sync_state")
    op.drop_column("compliance_entity_labels", "reviewed_at")
    op.drop_column("compliance_entity_labels", "reviewed_by")
    op.drop_column("compliance_entity_labels", "status")
