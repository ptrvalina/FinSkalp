"""Merge compliance queue priority and RFC-0020 ESA audit heads."""

from typing import Sequence, Union

from alembic import op

revision: str = "t2u3v4w5x6y7"
down_revision: Union[str, tuple[str, ...], None] = (
    "s1t2u3v4w5x6",
    "r0s1t2u3v4w5_rfc0020_esa_audit",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
