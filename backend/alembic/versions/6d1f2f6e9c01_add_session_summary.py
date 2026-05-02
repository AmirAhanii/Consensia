"""add debate_sessions.session_summary

Revision ID: 6d1f2f6e9c01
Revises: b7e3a1c40f0a
Create Date: 2026-05-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "6d1f2f6e9c01"
down_revision: Union[str, Sequence[str], None] = "b7e3a1c40f0a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "debate_sessions",
        sa.Column("session_summary", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("debate_sessions", "session_summary")

