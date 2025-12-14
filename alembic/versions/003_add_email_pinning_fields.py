"""Add email pinning fields

Revision ID: 003_add_email_pinning_fields
Revises: 002_add_email_threading_fields
Create Date: 2024-12-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_email_pinning_fields'
down_revision: Union[str, None] = '002_email_threading'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add pinned field to email_states table
    op.add_column('email_states', sa.Column('pinned', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('email_states', sa.Column('pinned_at', sa.DateTime(), nullable=True))
    
    # Create index for pinned field
    op.create_index('idx_email_states_pinned', 'email_states', ['pinned'], unique=False)


def downgrade() -> None:
    # Remove index
    op.drop_index('idx_email_states_pinned', table_name='email_states')
    
    # Remove columns
    op.drop_column('email_states', 'pinned_at')
    op.drop_column('email_states', 'pinned')

