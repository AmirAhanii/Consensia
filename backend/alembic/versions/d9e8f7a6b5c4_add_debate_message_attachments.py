"""add debate message attachments

Revision ID: d9e8f7a6b5c4
Revises: 6d1f2f6e9c01
Create Date: 2026-05-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9e8f7a6b5c4"
down_revision: Union[str, Sequence[str], None] = "6d1f2f6e9c01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "debate_message_attachments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("message_id", sa.String(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("data_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["debate_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["debate_messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_debate_message_attachments_user_id",
        "debate_message_attachments",
        ["user_id"],
    )
    op.create_index(
        "ix_debate_message_attachments_session_id",
        "debate_message_attachments",
        ["session_id"],
    )
    op.create_index(
        "ix_debate_message_attachments_message_id",
        "debate_message_attachments",
        ["message_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_debate_message_attachments_message_id", table_name="debate_message_attachments")
    op.drop_index("ix_debate_message_attachments_session_id", table_name="debate_message_attachments")
    op.drop_index("ix_debate_message_attachments_user_id", table_name="debate_message_attachments")
    op.drop_table("debate_message_attachments")