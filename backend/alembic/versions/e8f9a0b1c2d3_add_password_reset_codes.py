"""add password_reset_codes table

Revision ID: e8f9a0b1c2d3
Revises: 6d1f2f6e9c01
Create Date: 2026-05-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e8f9a0b1c2d3"
down_revision: Union[str, Sequence[str], None] = "6d1f2f6e9c01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "password_reset_codes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("code_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_hash"),
    )
    op.create_index(
        "ix_password_reset_codes_user_id",
        "password_reset_codes",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_password_reset_codes_user_id", table_name="password_reset_codes")
    op.drop_table("password_reset_codes")
