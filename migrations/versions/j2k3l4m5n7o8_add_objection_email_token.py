"""add email and confirmation token to amendment objections

Revision ID: j2k3l4m5n7o8
Revises: i1j2k3l4m5n6
Create Date: 2025-06-25 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'j2k3l4m5n7o8'
down_revision = 'i1j2k3l4m5n6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('amendment_objections', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('token', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('confirmed', sa.Boolean(), nullable=True, server_default=sa.false()))


def downgrade():
    with op.batch_alter_table('amendment_objections', schema=None) as batch_op:
        batch_op.drop_column('confirmed')
        batch_op.drop_column('token')
        batch_op.drop_column('email')
