"""RFC-0013 FinSkalp block sync — cursors, blocks, transfer index, sync locks."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p8q9r0s1t2u3"
down_revision: Union[str, None] = "o7p8q9r0s1t2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "finskalp_block_sync_cursors",
        sa.Column("chain", sa.String(32), primary_key=True),
        sa.Column("last_block_height", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_block_hash", sa.String(128), nullable=True),
        sa.Column("blocks_processed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("transactions_processed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "finskalp_chain_blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chain", sa.String(32), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("block_hash", sa.String(128), nullable=False),
        sa.Column("tx_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("block_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_finskalp_chain_blocks_chain", "finskalp_chain_blocks", ["chain"])
    op.create_index(
        "uq_finskalp_chain_block",
        "finskalp_chain_blocks",
        ["chain", "height"],
        unique=True,
    )

    op.create_table(
        "finskalp_indexed_transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chain", sa.String(32), nullable=False),
        sa.Column("address_key", sa.String(256), nullable=False),
        sa.Column("tx_hash", sa.String(128), nullable=False),
        sa.Column("source_address", sa.String(256), server_default="", nullable=False),
        sa.Column("target_address", sa.String(256), server_default="", nullable=False),
        sa.Column("asset", sa.String(32), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("block_height", sa.Integer(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "indexed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_finskalp_indexed_transfers_chain", "finskalp_indexed_transfers", ["chain"])
    op.create_index(
        "ix_finskalp_indexed_transfers_address_key",
        "finskalp_indexed_transfers",
        ["address_key"],
    )
    op.create_index("ix_finskalp_indexed_transfers_tx_hash", "finskalp_indexed_transfers", ["tx_hash"])
    op.create_index(
        "ix_finskalp_indexed_transfer_chain_addr",
        "finskalp_indexed_transfers",
        ["chain", "address_key"],
    )

    op.create_table(
        "finskalp_sync_locks",
        sa.Column("lock_name", sa.String(128), primary_key=True),
        sa.Column("holder_id", sa.String(128), nullable=False),
        sa.Column(
            "acquired_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("finskalp_sync_locks")
    op.drop_table("finskalp_indexed_transfers")
    op.drop_table("finskalp_chain_blocks")
    op.drop_table("finskalp_block_sync_cursors")
