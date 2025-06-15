"""add status column to motions

Revision ID: aa1234567890
Revises: fa1e1fb8c1a0
Create Date: 2025-06-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'aa1234567890'
down_revision = 'fa1e1fb8c1a0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('motions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=50), nullable=True))


def downgrade():
    with op.batch_alter_table('motions', schema=None) as batch_op:
        batch_op.drop_column('status')
