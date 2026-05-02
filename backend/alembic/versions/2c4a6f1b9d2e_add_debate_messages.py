"""add debate_messages table

Revision ID: 2c4a6f1b9d2e
Revises: f1a2b3c4d5e6
Create Date: 2026-05-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "2c4a6f1b9d2e"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "debate_messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.Column("author", sa.String(length=200), nullable=True),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("round_number", sa.Integer(), nullable=True),
        sa.Column("round_label", sa.String(length=80), nullable=True),
        sa.Column("persona_id", sa.String(length=120), nullable=True),
        sa.Column("persona_description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["debate_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_debate_messages_user_id", "debate_messages", ["user_id"])
    op.create_index("ix_debate_messages_session_id", "debate_messages", ["session_id"])
    op.create_index("ix_debate_messages_created_at", "debate_messages", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_debate_messages_created_at", table_name="debate_messages")
    op.drop_index("ix_debate_messages_session_id", table_name="debate_messages")
    op.drop_index("ix_debate_messages_user_id", table_name="debate_messages")
    op.drop_table("debate_messages")

