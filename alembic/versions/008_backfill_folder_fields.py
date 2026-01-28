"""Backfill folder and is_outgoing fields for existing emails

Revision ID: 008_backfill_folder
Revises: 007_sent_folder
Create Date: 2025-01-28

This migration backfills NULL values in the folder and is_outgoing columns
for existing emails that were created before these fields were added.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008_backfill_folder'
down_revision: Union[str, None] = '007_sent_folder'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Backfill NULL values with defaults
    # All existing emails are inbox emails (sent folder support is new)
    op.execute("UPDATE emails SET is_outgoing = false WHERE is_outgoing IS NULL")
    op.execute("UPDATE emails SET folder = 'inbox' WHERE folder IS NULL")


def downgrade() -> None:
    # No need to revert - the values are valid
    pass
