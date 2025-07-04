"""add extension_reason column

Revision ID: j7k8l9m0n1p2
Revises: j7k8l9m0n1o2
Create Date: 2025-06-26 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'j7k8l9m0n1p2'
down_revision = 'j7k8l9m0n1o2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('extension_reason', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.drop_column('extension_reason')
