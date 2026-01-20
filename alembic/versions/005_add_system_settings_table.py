"""add_system_settings_table

Revision ID: 005_system_settings
Revises: 004_supplier_part_validation
Create Date: 2025-01-20

This migration adds a system_settings table for storing runtime-configurable
settings like polling interval that persist across server restarts.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '005_system_settings'
down_revision: Union[str, None] = '004_supplier_part_validation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create system_settings table
    op.create_table(
        'system_settings',
        sa.Column('key', sa.String(100), primary_key=True),
        sa.Column('value', JSONB(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    # Drop system_settings table
    op.drop_table('system_settings')
