"""Add performance indexes on compliance registry labels."""

from alembic import op

revision = "a9b0c1d2e3f4"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_compliance_registry_labels_source",
        "compliance_registry_labels",
        ["source"],
    )
    op.create_index(
        "ix_compliance_registry_labels_sanctioned",
        "compliance_registry_labels",
        ["sanctioned"],
    )
    op.create_index(
        "ix_compliance_registry_labels_risk_score",
        "compliance_registry_labels",
        ["risk_score"],
    )


def downgrade() -> None:
    op.drop_index("ix_compliance_registry_labels_risk_score", table_name="compliance_registry_labels")
    op.drop_index("ix_compliance_registry_labels_sanctioned", table_name="compliance_registry_labels")
    op.drop_index("ix_compliance_registry_labels_source", table_name="compliance_registry_labels")
