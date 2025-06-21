"""add runoff timestamps to meetings

Revision ID: j7k8l9m0n1o2
Revises: i1j2k3l4m5n6
Create Date: 2025-06-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'j7k8l9m0n1o2'
down_revision = 'i1j2k3l4m5n6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('runoff_opens_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('runoff_closes_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.drop_column('runoff_closes_at')
        batch_op.drop_column('runoff_opens_at')
