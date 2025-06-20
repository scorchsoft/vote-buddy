"""drop member weight column

Revision ID: i1j2k3l4m5n6
Revises: ghijkl
Create Date: 2025-06-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'i1j2k3l4m5n6'
down_revision = 'ghijkl'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('members', schema=None) as batch_op:
        batch_op.drop_column('weight')


def downgrade():
    with op.batch_alter_table('members', schema=None) as batch_op:
        batch_op.add_column(sa.Column('weight', sa.Integer(), nullable=True))
