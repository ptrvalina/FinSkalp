"""Add optional queue_priority for server-side case queue ordering."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "s1t2u3v4w5x6"
down_revision: str | None = "l4m5n6o7p8q9"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("compliance_cases", sa.Column("queue_priority", sa.Integer(), nullable=True))
    op.create_index(
        "idx_cases_queue_priority",
        "compliance_cases",
        ["queue_priority"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_cases_queue_priority", table_name="compliance_cases")
    op.drop_column("compliance_cases", "queue_priority")
