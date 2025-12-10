"""Add user contact fields (phone and address)

Revision ID: 004_add_user_contact_fields
Revises: 003_add_scraped_data
Create Date: 2025-12-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_add_user_contact_fields'
down_revision: Union[str, None] = '003_add_scraped_data'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('phone', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('address_line1', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('address_line2', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('city', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('postal_code', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('country', sa.String(length=2), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'country')
    op.drop_column('users', 'postal_code')
    op.drop_column('users', 'city')
    op.drop_column('users', 'address_line2')
    op.drop_column('users', 'address_line1')
    op.drop_column('users', 'phone')

