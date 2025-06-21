"""add reason column to amendments

Revision ID: j8k9l0m1n2o3
Revises: j7k8l9m0n1p2
Create Date: 2025-06-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'j8k9l0m1n2o3'
down_revision = 'j7k8l9m0n1p2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('amendments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reason', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('amendments', schema=None) as batch_op:
        batch_op.drop_column('reason')
