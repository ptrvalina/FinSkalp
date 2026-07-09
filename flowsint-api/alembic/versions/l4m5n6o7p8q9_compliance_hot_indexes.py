"""Revision: hot-table indexes for compliance workload (pgHero audit targets)."""

from typing import Sequence

from alembic import op

revision: str = "l4m5n6o7p8q9"
down_revision: str | None = "k3l4m5n6o7p8_graph_views"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "idx_entity_labels_status_added",
        "compliance_entity_labels",
        ["status", "added_at"],
        unique=False,
    )
    op.create_index(
        "idx_entity_labels_risk_score",
        "compliance_entity_labels",
        ["risk_score"],
        unique=False,
        postgresql_where="risk_score IS NOT NULL",
    )
    op.create_index(
        "idx_cases_workflow_updated",
        "compliance_cases",
        ["workflow_status", "updated_at"],
        unique=False,
    )
    op.create_index(
        "idx_cases_owner_workflow",
        "compliance_cases",
        ["owner_id", "workflow_status"],
        unique=False,
    )
    op.create_index(
        "idx_audit_log_created",
        "compliance_audit_log",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "idx_audit_log_action_created",
        "compliance_audit_log",
        ["action", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_fusion_runs_case_status",
        "compliance_fusion_runs",
        ["case_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_registry_labels_risk",
        "compliance_registry_labels",
        ["risk_score"],
        unique=False,
        postgresql_where="risk_score IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_index("idx_registry_labels_risk", table_name="compliance_registry_labels")
    op.drop_index("idx_fusion_runs_case_status", table_name="compliance_fusion_runs")
    op.drop_index("idx_audit_log_action_created", table_name="compliance_audit_log")
    op.drop_index("idx_audit_log_created", table_name="compliance_audit_log")
    op.drop_index("idx_cases_owner_workflow", table_name="compliance_cases")
    op.drop_index("idx_cases_workflow_updated", table_name="compliance_cases")
    op.drop_index("idx_entity_labels_risk_score", table_name="compliance_entity_labels")
    op.drop_index("idx_entity_labels_status_added", table_name="compliance_entity_labels")
