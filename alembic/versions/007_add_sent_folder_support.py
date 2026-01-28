"""Add sent folder support for follow-up conversations

Revision ID: 007_sent_folder
Revises: 006_followup_sent
Create Date: 2025-01-28

This migration adds support for monitoring the Sent folder to enable
complete conversation thread display (including sent follow-ups and replies).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007_sent_folder'
down_revision: Union[str, None] = '006_followup_sent'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add sent_delta_token to delta_tokens table for tracking sent folder changes
    op.add_column('delta_tokens', sa.Column('sent_delta_token', sa.Text(), nullable=True))

    # Add folder tracking to emails table
    op.add_column('emails', sa.Column('folder', sa.String(50), nullable=True, server_default='inbox'))
    op.add_column('emails', sa.Column('is_outgoing', sa.Boolean(), nullable=True, server_default='false'))
    op.create_index('idx_emails_folder', 'emails', ['folder'])


def downgrade() -> None:
    # Remove index and columns
    op.drop_index('idx_emails_folder', table_name='emails')
    op.drop_column('emails', 'is_outgoing')
    op.drop_column('emails', 'folder')
    op.drop_column('delta_tokens', 'sent_delta_token')
