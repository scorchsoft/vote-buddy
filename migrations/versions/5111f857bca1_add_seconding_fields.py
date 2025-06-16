"""add seconded_at and method to amendments

Revision ID: 5111f857bca1
Revises: fa1e1fb8c1a0
Create Date: 2025-06-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '5111f857bca1'
down_revision = 'fa1e1fb8c1a0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('amendments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('seconded_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('seconded_method', sa.String(length=50), nullable=True))


def downgrade():
    with op.batch_alter_table('amendments', schema=None) as batch_op:
        batch_op.drop_column('seconded_method')
        batch_op.drop_column('seconded_at')
