"""add motion withdraw/edit request fields

Revision ID: m0n1o2p3
Revises: k1l2m3n4o5p6
Create Date: 2025-06-30 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'm0n1o2p3'
down_revision = 'k1l2m3n4o5p6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('motions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('withdrawn', sa.Boolean(), nullable=True, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('modified_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('withdrawal_requested_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('chair_approved_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('board_approved_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('motions', schema=None) as batch_op:
        batch_op.drop_column('board_approved_at')
        batch_op.drop_column('chair_approved_at')
        batch_op.drop_column('withdrawal_requested_at')
        batch_op.drop_column('modified_at')
        batch_op.drop_column('withdrawn')
