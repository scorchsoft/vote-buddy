"""add tie_break_method to runoffs

Revision ID: j7k8l9m0n1
Revises: i1j2k3l4m5n6
Create Date: 2025-06-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'j7k8l9m0n1'
down_revision = 'i1j2k3l4m5n6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('runoffs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tie_break_method', sa.String(length=20), nullable=True))


def downgrade():
    with op.batch_alter_table('runoffs', schema=None) as batch_op:
        batch_op.drop_column('tie_break_method')
