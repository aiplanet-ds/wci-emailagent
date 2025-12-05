"""add_oauth_tokens_table

Revision ID: 001_oauth_tokens
Revises: 
Create Date: 2025-12-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_oauth_tokens'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'oauth_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('service_name', sa.String(length=100), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_type', sa.String(length=50), nullable=True, default='Bearer'),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('obtained_via', sa.String(length=50), nullable=True),
        sa.Column('scope', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_oauth_tokens_id', 'oauth_tokens', ['id'], unique=False)
    op.create_index('ix_oauth_tokens_service_name', 'oauth_tokens', ['service_name'], unique=True)
    op.create_index('ix_oauth_tokens_expires_at', 'oauth_tokens', ['expires_at'], unique=False)
    op.create_index('ix_oauth_tokens_service_expires', 'oauth_tokens', ['service_name', 'expires_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_oauth_tokens_service_expires', table_name='oauth_tokens')
    op.drop_index('ix_oauth_tokens_expires_at', table_name='oauth_tokens')
    op.drop_index('ix_oauth_tokens_service_name', table_name='oauth_tokens')
    op.drop_index('ix_oauth_tokens_id', table_name='oauth_tokens')
    op.drop_table('oauth_tokens')

