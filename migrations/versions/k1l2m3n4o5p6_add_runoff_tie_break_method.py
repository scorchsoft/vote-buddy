"""add tie_break_method to runoffs

Revision ID: k1l2m3n4o5p6
Revises: j7k8l9m0n1p2
Create Date: 2025-06-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'k1l2m3n4o5p6'
down_revision = 'j7k8l9m0n1p2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('runoffs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tie_break_method', sa.String(length=20), nullable=True))


def downgrade():
    with op.batch_alter_table('runoffs', schema=None) as batch_op:
        batch_op.drop_column('tie_break_method')
