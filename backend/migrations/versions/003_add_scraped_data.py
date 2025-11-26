"""Add scraped_data table

Revision ID: 003_add_scraped_data
Revises: 002_add_live_config
Create Date: 2025-11-26

Adds the scraped_data table for storing cricket data from Play-Cricket
in the database instead of a JSON file. Implements stale-while-revalidate
pattern for resilience.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_scraped_data'
down_revision: Union[str, None] = '002_add_live_config'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('scraped_data',
        sa.Column('id', sa.Integer(), nullable=False, default=1),
        sa.Column('teams_data', sa.Text(), nullable=True),
        sa.Column('fixtures_data', sa.Text(), nullable=True),
        sa.Column('results_data', sa.Text(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.Column('last_scrape_success', sa.Boolean(), nullable=True, default=True),
        sa.Column('scrape_error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('scraped_data')
