"""add favorite_personas table

Revision ID: c9d8e7f6a5b4
Revises: f1a2b3c4d5e6, 8868e829e3fd
Create Date: 2026-04-30 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, Sequence[str], None] = ("f1a2b3c4d5e6", "8868e829e3fd")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "favorite_personas",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("icon", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_favorite_personas_user_id", "favorite_personas", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_favorite_personas_user_id", table_name="favorite_personas")
    op.drop_table("favorite_personas")
