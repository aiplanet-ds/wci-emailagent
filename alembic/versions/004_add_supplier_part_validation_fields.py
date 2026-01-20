"""add_supplier_part_validation_fields

Revision ID: 004_supplier_part_validation
Revises: 003_add_email_pinning_fields
Create Date: 2025-12-17

This migration adds fields to track supplier-part relationship validation:
1. BomImpactResult: supplier_part_validated, supplier_part_validation_error
2. EmailState: epicor_validation_performed, epicor_validation_result
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '004_supplier_part_validation'
down_revision: Union[str, None] = '003_add_email_pinning_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add supplier-part validation fields to bom_impact_results table
    op.add_column('bom_impact_results', sa.Column('supplier_part_validated', sa.Boolean(), nullable=True, default=False))
    op.add_column('bom_impact_results', sa.Column('supplier_part_validation_error', sa.Text(), nullable=True))
    
    # Add Epicor validation fields to email_states table
    op.add_column('email_states', sa.Column('epicor_validation_performed', sa.Boolean(), nullable=True, default=False))
    op.add_column('email_states', sa.Column('epicor_validation_result', JSONB(), nullable=True))


def downgrade() -> None:
    # Remove Epicor validation fields from email_states table
    op.drop_column('email_states', 'epicor_validation_result')
    op.drop_column('email_states', 'epicor_validation_performed')
    
    # Remove supplier-part validation fields from bom_impact_results table
    op.drop_column('bom_impact_results', 'supplier_part_validation_error')
    op.drop_column('bom_impact_results', 'supplier_part_validated')

