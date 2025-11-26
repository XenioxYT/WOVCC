"""Initial migration - baseline schema

Revision ID: 001_initial
Revises: 
Create Date: 2025-11-26

This is a baseline migration representing the existing database schema.
For existing databases, stamp this revision without running it.
For new databases, this will create all tables.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('activation_token', sa.String(length=255), nullable=True),
        sa.Column('membership_tier', sa.String(length=100), nullable=True),
        sa.Column('is_member', sa.Boolean(), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True),
        sa.Column('newsletter', sa.Boolean(), nullable=True),
        sa.Column('stripe_customer_id', sa.String(length=255), nullable=True),
        sa.Column('payment_status', sa.String(length=50), nullable=True),
        sa.Column('has_spouse_card', sa.Boolean(), nullable=True),
        sa.Column('membership_start_date', sa.DateTime(), nullable=True),
        sa.Column('membership_expiry_date', sa.DateTime(), nullable=True),
        sa.Column('join_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_activation_token'), 'users', ['activation_token'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_stripe_customer_id'), 'users', ['stripe_customer_id'], unique=False)

    # Pending registrations table
    op.create_table('pending_registrations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('activation_token', sa.String(length=255), nullable=False),
        sa.Column('newsletter', sa.Boolean(), nullable=True),
        sa.Column('include_spouse_card', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pending_registrations_activation_token'), 'pending_registrations', ['activation_token'], unique=True)
    op.create_index(op.f('ix_pending_registrations_email'), 'pending_registrations', ['email'], unique=False)
    op.create_index(op.f('ix_pending_registrations_id'), 'pending_registrations', ['id'], unique=False)

    # Events table
    op.create_table('events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('short_description', sa.String(length=255), nullable=False),
        sa.Column('long_description', sa.Text(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('time', sa.String(length=50), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('is_recurring', sa.Boolean(), nullable=True),
        sa.Column('recurrence_pattern', sa.String(length=50), nullable=True),
        sa.Column('recurrence_end_date', sa.DateTime(), nullable=True),
        sa.Column('parent_event_id', sa.Integer(), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=True),
        sa.Column('interested_count', sa.Integer(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['parent_event_id'], ['events.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_events_category'), 'events', ['category'], unique=False)
    op.create_index(op.f('ix_events_date'), 'events', ['date'], unique=False)
    op.create_index(op.f('ix_events_id'), 'events', ['id'], unique=False)
    op.create_index(op.f('ix_events_is_published'), 'events', ['is_published'], unique=False)
    op.create_index(op.f('ix_events_parent_event_id'), 'events', ['parent_event_id'], unique=False)

    # Event interests table
    op.create_table('event_interests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('user_email', sa.String(length=255), nullable=True),
        sa.Column('user_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_event_interests_event_id'), 'event_interests', ['event_id'], unique=False)
    op.create_index(op.f('ix_event_interests_id'), 'event_interests', ['id'], unique=False)
    op.create_index(op.f('ix_event_interests_user_id'), 'event_interests', ['user_id'], unique=False)

    # Content snippets table
    op.create_table('content_snippets',
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('key')
    )

    # Sponsors table
    op.create_table('sponsors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('logo_url', sa.String(length=500), nullable=False),
        sa.Column('website_url', sa.String(length=500), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sponsors_display_order'), 'sponsors', ['display_order'], unique=False)
    op.create_index(op.f('ix_sponsors_id'), 'sponsors', ['id'], unique=False)
    op.create_index(op.f('ix_sponsors_is_active'), 'sponsors', ['is_active'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sponsors_is_active'), table_name='sponsors')
    op.drop_index(op.f('ix_sponsors_id'), table_name='sponsors')
    op.drop_index(op.f('ix_sponsors_display_order'), table_name='sponsors')
    op.drop_table('sponsors')
    op.drop_table('content_snippets')
    op.drop_index(op.f('ix_event_interests_user_id'), table_name='event_interests')
    op.drop_index(op.f('ix_event_interests_id'), table_name='event_interests')
    op.drop_index(op.f('ix_event_interests_event_id'), table_name='event_interests')
    op.drop_table('event_interests')
    op.drop_index(op.f('ix_events_parent_event_id'), table_name='events')
    op.drop_index(op.f('ix_events_is_published'), table_name='events')
    op.drop_index(op.f('ix_events_id'), table_name='events')
    op.drop_index(op.f('ix_events_date'), table_name='events')
    op.drop_index(op.f('ix_events_category'), table_name='events')
    op.drop_table('events')
    op.drop_index(op.f('ix_pending_registrations_id'), table_name='pending_registrations')
    op.drop_index(op.f('ix_pending_registrations_email'), table_name='pending_registrations')
    op.drop_index(op.f('ix_pending_registrations_activation_token'), table_name='pending_registrations')
    op.drop_table('pending_registrations')
    op.drop_index(op.f('ix_users_stripe_customer_id'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_activation_token'), table_name='users')
    op.drop_table('users')
