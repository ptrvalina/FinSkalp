"""RFC-0020 ESA security audit Postgres table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "r0s1t2u3v4w5_rfc0020_esa_audit"
down_revision: Union[str, None] = "q9r0s1t2u3v4_rfc0017_eccf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "esa_security_audit",
        sa.Column("entry_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource", sa.String(256), server_default="", nullable=False),
        sa.Column("outcome", sa.String(32), server_default="success", nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=True),
        sa.PrimaryKeyConstraint("entry_id"),
    )
    op.create_index("ix_esa_security_audit_event_type", "esa_security_audit", ["event_type"])
    op.create_index("ix_esa_security_audit_timestamp", "esa_security_audit", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_esa_security_audit_timestamp", table_name="esa_security_audit")
    op.drop_index("ix_esa_security_audit_event_type", table_name="esa_security_audit")
    op.drop_table("esa_security_audit")
