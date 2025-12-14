"""add_email_threading_fields

Add conversation threading fields to emails table for Microsoft Graph
conversation tracking and email thread grouping.

Revision ID: 002_email_threading
Revises: 1b08d75a6bc0
Create Date: 2025-12-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_email_threading'
down_revision: Union[str, None] = '1b08d75a6bc0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add threading fields to emails table
    op.add_column('emails', sa.Column('conversation_id', sa.String(length=255), nullable=True))
    op.add_column('emails', sa.Column('conversation_index', sa.Text(), nullable=True))
    op.add_column('emails', sa.Column('is_reply', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('emails', sa.Column('is_forward', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('emails', sa.Column('thread_subject', sa.Text(), nullable=True))

    # Create index on conversation_id for efficient thread grouping queries
    op.create_index('ix_emails_conversation_id', 'emails', ['conversation_id'], unique=False)


def downgrade() -> None:
    # Drop index first
    op.drop_index('ix_emails_conversation_id', table_name='emails')

    # Drop columns
    op.drop_column('emails', 'thread_subject')
    op.drop_column('emails', 'is_forward')
    op.drop_column('emails', 'is_reply')
    op.drop_column('emails', 'conversation_index')
    op.drop_column('emails', 'conversation_id')

