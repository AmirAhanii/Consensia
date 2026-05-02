"""add debate_sessions table

Revision ID: f1a2b3c4d5e6
Revises: ea83cacc7ef9
Create Date: 2026-04-29 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'ea83cacc7ef9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'debate_sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(120), nullable=False, server_default='New Debate'),
        sa.Column('question', sa.Text(), nullable=False, server_default=''),
        sa.Column('personas', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_debate_sessions_user_id', 'debate_sessions', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_debate_sessions_user_id', 'debate_sessions')
    op.drop_table('debate_sessions')
