"""add early public stage1 results flag

Revision ID: p1q2r3s4
Revises: o3p4q5r6
Create Date: 2025-07-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'p1q2r3s4'
down_revision = 'o3p4q5r6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('early_public_results', sa.Boolean(), nullable=True, server_default=sa.false()))


def downgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.drop_column('early_public_results')
