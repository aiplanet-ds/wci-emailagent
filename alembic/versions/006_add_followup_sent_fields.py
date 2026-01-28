"""Add followup_sent tracking fields to email_states

Revision ID: 006_followup_sent
Revises: 005_system_settings
Create Date: 2025-01-28

This migration adds fields to track when a follow-up email has been sent
via the application's direct send feature.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_followup_sent'
down_revision: Union[str, None] = '005_system_settings'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add followup_sent field to track if a follow-up was sent
    op.add_column('email_states', sa.Column('followup_sent', sa.Boolean(), nullable=True, server_default='false'))
    # Add followup_sent_at field to track when the follow-up was sent
    op.add_column('email_states', sa.Column('followup_sent_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove columns
    op.drop_column('email_states', 'followup_sent_at')
    op.drop_column('email_states', 'followup_sent')
