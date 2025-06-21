"""add manual tally fields to meetings

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
Create Date: 2025-07-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'l2m3n4o5p6q7'
down_revision = 'k1l2m3n4o5p6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('stage1_manual_votes', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('stage2_manual_for', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('stage2_manual_against', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('stage2_manual_abstain', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.drop_column('stage2_manual_abstain')
        batch_op.drop_column('stage2_manual_against')
        batch_op.drop_column('stage2_manual_for')
        batch_op.drop_column('stage1_manual_votes')
