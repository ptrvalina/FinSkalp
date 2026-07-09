"""Add case workflow, RBAC, batch screening, watchlist, webhooks."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "h0i1j2k3l4m5"
down_revision = "g9h0i1j2k3l4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("compliance_cases", sa.Column("workflow_status", sa.String(32), server_default="new"))
    op.add_column("compliance_cases", sa.Column("assignee_id", sa.Uuid(), nullable=True))
    op.add_column("compliance_cases", sa.Column("priority", sa.String(16), server_default="normal"))
    op.add_column("compliance_cases", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("compliance_cases", sa.Column("sla_hours", sa.Integer(), nullable=True))
    op.add_column("compliance_cases", sa.Column("sla_breached", sa.Boolean(), server_default="false"))
    op.create_index("ix_compliance_cases_assignee_id", "compliance_cases", ["assignee_id"])

    op.create_table(
        "compliance_case_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_compliance_case_comments_case_id", "compliance_case_comments", ["case_id"])

    op.create_table(
        "compliance_user_roles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(32), server_default="analyst"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "compliance_batch_screen_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(32), server_default="pending"),
        sa.Column("total", sa.Integer(), server_default="0"),
        sa.Column("processed", sa.Integer(), server_default="0"),
        sa.Column("celery_task_id", sa.String(64), nullable=True),
        sa.Column("summary", postgresql.JSONB(), nullable=True),
        sa.Column("results", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_batch_screen_owner", "compliance_batch_screen_jobs", ["owner_id"])

    op.create_table(
        "compliance_watchlist_subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("address", sa.String(128), nullable=False),
        sa.Column("chain", sa.String(16), server_default="tron"),
        sa.Column("label", sa.String(128), nullable=True),
        sa.Column("active", sa.Boolean(), server_default="true"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_hit_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_watchlist_owner_address",
        "compliance_watchlist_subscriptions",
        ["owner_id", "address", "chain"],
        unique=True,
    )

    op.create_table(
        "compliance_webhook_endpoints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bank_id", sa.String(64), nullable=False),
        sa.Column("secret_hint", sa.String(16), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true"),
        sa.Column("outbound_url", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bank_id"),
    )


def downgrade() -> None:
    op.drop_table("compliance_webhook_endpoints")
    op.drop_table("compliance_watchlist_subscriptions")
    op.drop_table("compliance_batch_screen_jobs")
    op.drop_table("compliance_user_roles")
    op.drop_table("compliance_case_comments")
    op.drop_index("ix_compliance_cases_assignee_id", "compliance_cases")
    for col in ("sla_breached", "sla_hours", "due_at", "priority", "assignee_id", "workflow_status"):
        op.drop_column("compliance_cases", col)
