"""add is_admin on users and debate_rate_buckets for daily quotas

Revision ID: b7e3a1c40f0a
Revises: 2c4a6f1b9d2e, c9d8e7f6a5b4
Create Date: 2026-05-01 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b7e3a1c40f0a"
down_revision: Union[str, Sequence[str], None] = ("2c4a6f1b9d2e", "c9d8e7f6a5b4")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_table(
        "debate_rate_buckets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("subject", sa.String(length=128), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kind", "subject", "day", name="uq_debate_rate_bucket_day"),
    )


def downgrade() -> None:
    op.drop_table("debate_rate_buckets")
    op.drop_column("users", "is_admin")
