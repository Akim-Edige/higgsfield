"""Initial schema with all tables.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-10-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('handle', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=False, server_default='user'),
        sa.Column('credit_balance', sa.Numeric(precision=12, scale=4), nullable=False, server_default='0'),
        sa.Column('flags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_handle', 'users', ['handle'], unique=True)

    # Create chats table
    op.create_table(
        'chats',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_message_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chats_user_id', 'chats', ['user_id'])
    op.create_index('ix_chats_user_created', 'chats', ['user_id', sa.text('created_at DESC'), sa.text('id DESC')])
    op.create_index('ix_chats_user_last_message', 'chats', ['user_id', sa.text('last_message_at DESC'), sa.text('id DESC')])

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chat_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('author_type', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=True),
        sa.Column('content_text', sa.Text(), nullable=True),
        sa.Column('render_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('reply_to_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('moderation', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('token_usage', sa.Integer(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_messages_chat_id', 'messages', ['chat_id'])
    op.create_index('ix_messages_chat_created', 'messages', ['chat_id', sa.text('created_at DESC'), sa.text('id DESC')])

    # Create attachments table
    op.create_table(
        'attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chat_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('mime', sa.Text(), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('storage_url', sa.Text(), nullable=False),
        sa.Column('provider_url', sa.Text(), nullable=True),
        sa.Column('sha256', sa.Text(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('blurhash', sa.Text(), nullable=True),
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_attachments_user_id', 'attachments', ['user_id'])
    op.create_index('ix_attachments_chat_id', 'attachments', ['chat_id'])
    op.create_index('ix_attachments_message_id', 'attachments', ['message_id'])
    op.create_index('ix_attachments_chat_created', 'attachments', ['chat_id', sa.text('created_at DESC')])
    op.create_index('ix_attachments_sha256', 'attachments', ['sha256'])

    # Create options table
    op.create_table(
        'options',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rank', sa.SmallInteger(), nullable=False),
        sa.Column('tool_type', sa.String(), nullable=False),
        sa.Column('model_key', sa.Text(), nullable=False),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('enhanced_prompt', sa.Text(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Numeric(), nullable=True),
        sa.Column('est_cost', sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column('est_latency_ms', sa.Integer(), nullable=True),
        sa.Column('requires_attachment', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('result_url', sa.Text(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_options_message_id', 'options', ['message_id'])
    op.create_index('ix_options_message_rank', 'options', ['message_id', 'rank'], unique=True)
    op.create_index('ix_options_model_key', 'options', ['model_key'])

    # Create generation_jobs table
    op.create_table(
        'generation_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('option_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('idempotency_key', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='PENDING'),
        sa.Column('provider', sa.String(), nullable=False, server_default='higgsfield'),
        sa.Column('provider_job_set_id', sa.Text(), nullable=True),
        sa.Column('progress', sa.SmallInteger(), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error_code', sa.Text(), nullable=True),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('last_polled_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('next_poll_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('timeout_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('started_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('finished_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('output_urls', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_meta', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('trace_id', sa.Text(), nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_generation_jobs_option_id', 'generation_jobs', ['option_id'])
    op.create_index('ix_generation_jobs_user_id', 'generation_jobs', ['user_id'])
    op.create_index('ix_generation_jobs_status', 'generation_jobs', ['status'])
    op.create_index('ix_generation_jobs_next_poll_at', 'generation_jobs', ['next_poll_at'])
    op.create_index('ix_jobs_user_option_idem', 'generation_jobs', ['user_id', 'option_id', 'idempotency_key'], unique=True)
    op.create_index('ix_jobs_provider_job_set_id', 'generation_jobs', ['provider_job_set_id'], unique=True)
    op.create_index('ix_jobs_status_updated', 'generation_jobs', ['status', sa.text('updated_at')])
    op.create_index(
        'ix_jobs_next_poll',
        'generation_jobs',
        ['next_poll_at'],
        postgresql_where=sa.text("status IN ('PENDING', 'RUNNING')")
    )

    # Create demo user
    op.execute("""
        INSERT INTO users (id, handle, role, credit_balance)
        VALUES ('00000000-0000-0000-0000-000000000001', 'demo', 'user', 1000.0)
    """)


def downgrade() -> None:
    op.drop_table('generation_jobs')
    op.drop_table('options')
    op.drop_table('attachments')
    op.drop_table('messages')
    op.drop_table('chats')
    op.drop_table('users')

