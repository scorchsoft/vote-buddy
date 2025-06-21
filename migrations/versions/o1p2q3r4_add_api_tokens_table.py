"""add api tokens table

Revision ID: o1p2q3r4
Revises: n1o2p3q4
Create Date: 2025-07-07 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = 'o1p2q3r4'
down_revision = 'n1o2p3q4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'api_tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table('api_tokens')
