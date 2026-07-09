"""RFC-0003 Knowledge Graph extensions — versioning, snapshots, relation/evidence columns."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "o7p8q9r0s1t2"
down_revision: Union[str, None] = "n6o7p8q9r0s1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "finskalp_entity_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("changed_by", sa.String(128), server_default="system", nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_finskalp_entity_versions_entity_id", "finskalp_entity_versions", ["entity_id"])
    op.create_index(
        "uq_finskalp_entity_version",
        "finskalp_entity_versions",
        ["entity_id", "version"],
        unique=True,
    )

    op.create_table(
        "finskalp_relation_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("relation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("changed_by", sa.String(128), server_default="system", nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_finskalp_relation_versions_relation_id", "finskalp_relation_versions", ["relation_id"])

    op.create_table(
        "finskalp_graph_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_finskalp_graph_snapshots_tenant_id", "finskalp_graph_snapshots", ["tenant_id"])
    op.create_index("ix_finskalp_graph_snapshots_as_of", "finskalp_graph_snapshots", ["as_of"])

    op.add_column(
        "finskalp_entity_relations",
        sa.Column("source", sa.String(64), server_default="unknown", nullable=False),
    )
    op.add_column(
        "finskalp_entity_relations",
        sa.Column("acquisition_method", sa.String(64), server_default="inferred", nullable=False),
    )
    op.add_column(
        "finskalp_entity_relations",
        sa.Column("actor", sa.String(128), server_default="system", nullable=False),
    )
    op.add_column(
        "finskalp_entity_relations",
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "finskalp_entity_relations",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column(
        "finskalp_entity_relations",
        sa.Column("history", postgresql.JSONB(), server_default="[]", nullable=False),
    )

    op.add_column(
        "finskalp_evidence",
        sa.Column("acquisition_method", sa.String(64), server_default="automated_collection", nullable=False),
    )
    op.add_column(
        "finskalp_evidence",
        sa.Column("digital_signature", sa.String(256), nullable=True),
    )
    op.add_column(
        "finskalp_evidence",
        sa.Column("original_uri", sa.Text(), nullable=True),
    )
    op.add_column(
        "finskalp_evidence",
        sa.Column("retention_policy", sa.String(64), server_default="standard_7y", nullable=False),
    )
    op.add_column(
        "finskalp_evidence",
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("finskalp_evidence", "valid_until")
    op.drop_column("finskalp_evidence", "retention_policy")
    op.drop_column("finskalp_evidence", "original_uri")
    op.drop_column("finskalp_evidence", "digital_signature")
    op.drop_column("finskalp_evidence", "acquisition_method")

    op.drop_column("finskalp_entity_relations", "history")
    op.drop_column("finskalp_entity_relations", "version")
    op.drop_column("finskalp_entity_relations", "valid_until")
    op.drop_column("finskalp_entity_relations", "actor")
    op.drop_column("finskalp_entity_relations", "acquisition_method")
    op.drop_column("finskalp_entity_relations", "source")

    op.drop_table("finskalp_graph_snapshots")
    op.drop_table("finskalp_relation_versions")
    op.drop_table("finskalp_entity_versions")
