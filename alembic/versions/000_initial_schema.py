"""initial schema - create core tables

Revision ID: 000_initial_schema
Revises:
Create Date: 2025-12-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '000_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('msal_account_id', sa.String(length=255), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('preferences', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_is_active', 'users', ['is_active'], unique=False)

    # Vendors table
    op.create_table(
        'vendors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vendor_id', sa.String(length=100), nullable=False),
        sa.Column('vendor_name', sa.String(length=255), nullable=False),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('verified', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('verified_domains', postgresql.JSONB(), nullable=True),
        sa.Column('last_synced_from_epicor', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_vendors_id', 'vendors', ['id'], unique=False)
    op.create_index('ix_vendors_vendor_id', 'vendors', ['vendor_id'], unique=True)
    op.create_index('ix_vendors_contact_email', 'vendors', ['contact_email'], unique=False)
    op.create_index('ix_vendors_verified', 'vendors', ['verified'], unique=False)

    # Emails table
    op.create_table(
        'emails',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.String(length=500), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.Text(), nullable=True),
        sa.Column('sender_email', sa.String(length=255), nullable=True),
        sa.Column('sender_name', sa.String(length=255), nullable=True),
        sa.Column('received_at', sa.DateTime(), nullable=True),
        sa.Column('has_attachments', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('body_text', sa.Text(), nullable=True),
        sa.Column('body_html', sa.Text(), nullable=True),
        sa.Column('supplier_info', postgresql.JSONB(), nullable=True),
        sa.Column('price_change_summary', postgresql.JSONB(), nullable=True),
        sa.Column('affected_products', postgresql.JSONB(), nullable=True),
        sa.Column('additional_details', postgresql.JSONB(), nullable=True),
        sa.Column('raw_email_data', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_emails_id', 'emails', ['id'], unique=False)
    op.create_index('ix_emails_message_id', 'emails', ['message_id'], unique=True)
    op.create_index('ix_emails_user_id', 'emails', ['user_id'], unique=False)
    op.create_index('ix_emails_sender_email', 'emails', ['sender_email'], unique=False)
    op.create_index('ix_emails_received_at', 'emails', ['received_at'], unique=False)
    op.create_index('ix_emails_created_at', 'emails', ['created_at'], unique=False)

    # Email states table
    op.create_table(
        'email_states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.String(length=500), nullable=False),
        sa.Column('email_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('processed', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('processed_by_id', sa.Integer(), nullable=True),
        sa.Column('is_price_change', sa.Boolean(), nullable=True),
        sa.Column('llm_confidence', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('llm_reasoning', sa.Text(), nullable=True),
        sa.Column('awaiting_llm_detection', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('llm_detection_performed', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('epicor_synced', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('epicor_synced_at', sa.DateTime(), nullable=True),
        sa.Column('epicor_sync_attempts', sa.Integer(), nullable=True, server_default=sa.text('0')),
        sa.Column('needs_info', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('selected_missing_fields', postgresql.JSONB(), nullable=True),
        sa.Column('followup_draft', sa.Text(), nullable=True),
        sa.Column('vendor_verified', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('verification_status', sa.String(length=50), nullable=True, server_default=sa.text("'pending_review'")),
        sa.Column('verification_method', sa.String(length=50), nullable=True),
        sa.Column('vendor_id', sa.Integer(), nullable=True),
        sa.Column('manually_approved_by_id', sa.Integer(), nullable=True),
        sa.Column('manually_approved_at', sa.DateTime(), nullable=True),
        sa.Column('flagged_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['email_id'], ['emails.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['processed_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id']),
        sa.ForeignKeyConstraint(['manually_approved_by_id'], ['users.id']),
    )
    op.create_index('ix_email_states_id', 'email_states', ['id'], unique=False)
    op.create_index('ix_email_states_message_id', 'email_states', ['message_id'], unique=True)
    op.create_index('ix_email_states_email_id', 'email_states', ['email_id'], unique=False)
    op.create_index('ix_email_states_user_id', 'email_states', ['user_id'], unique=False)
    op.create_index('ix_email_states_processed', 'email_states', ['processed'], unique=False)
    op.create_index('ix_email_states_epicor_synced', 'email_states', ['epicor_synced'], unique=False)
    op.create_index('ix_email_states_verification_status', 'email_states', ['verification_status'], unique=False)
    op.create_index('ix_email_states_created_at', 'email_states', ['created_at'], unique=False)

    # Attachments table
    op.create_table(
        'attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=500), nullable=True),
        sa.Column('content_type', sa.String(length=100), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('storage_path', sa.Text(), nullable=True),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('processed', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['email_id'], ['emails.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_attachments_id', 'attachments', ['id'], unique=False)
    op.create_index('ix_attachments_email_id', 'attachments', ['email_id'], unique=False)
    op.create_index('ix_attachments_filename', 'attachments', ['filename'], unique=False)

    # Epicor sync results table
    op.create_table(
        'epicor_sync_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('sync_status', sa.String(length=50), nullable=True),
        sa.Column('total_products', sa.Integer(), nullable=True, server_default=sa.text('0')),
        sa.Column('successful_updates', sa.Integer(), nullable=True, server_default=sa.text('0')),
        sa.Column('failed_updates', sa.Integer(), nullable=True, server_default=sa.text('0')),
        sa.Column('results_summary', postgresql.JSONB(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('synced_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['email_id'], ['emails.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )
    op.create_index('ix_epicor_sync_results_id', 'epicor_sync_results', ['id'], unique=False)
    op.create_index('ix_epicor_sync_results_email_id', 'epicor_sync_results', ['email_id'], unique=False)
    op.create_index('ix_epicor_sync_results_sync_status', 'epicor_sync_results', ['sync_status'], unique=False)
    op.create_index('ix_epicor_sync_results_synced_at', 'epicor_sync_results', ['synced_at'], unique=False)

    # Delta tokens table
    op.create_table(
        'delta_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('delta_token', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index('ix_delta_tokens_id', 'delta_tokens', ['id'], unique=False)
    op.create_index('ix_delta_tokens_user_id', 'delta_tokens', ['user_id'], unique=False)

    # Audit logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('email_id', sa.Integer(), nullable=True),
        sa.Column('action_type', sa.String(length=100), nullable=True),
        sa.Column('action_details', postgresql.JSONB(), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['email_id'], ['emails.id']),
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'], unique=False)
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'], unique=False)
    op.create_index('ix_audit_logs_email_id', 'audit_logs', ['email_id'], unique=False)
    op.create_index('ix_audit_logs_action_type', 'audit_logs', ['action_type'], unique=False)
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('delta_tokens')
    op.drop_table('epicor_sync_results')
    op.drop_table('attachments')
    op.drop_table('email_states')
    op.drop_table('emails')
    op.drop_table('vendors')
    op.drop_table('users')
