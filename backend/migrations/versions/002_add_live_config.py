"""Add live_config table

Revision ID: 002_add_live_config
Revises: 001_initial
Create Date: 2025-11-26

Adds the live_config table for storing livestream configuration
in the database instead of a JSON file.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_live_config'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('live_config',
        sa.Column('id', sa.Integer(), nullable=False, default=1),
        sa.Column('is_live', sa.Boolean(), nullable=False, default=False),
        sa.Column('livestream_url', sa.String(length=500), nullable=False, default=''),
        sa.Column('selected_match_data', sa.Text(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('live_config')
