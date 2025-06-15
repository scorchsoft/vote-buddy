"""add quorum and stage locking fields

Revision ID: f641fa4204d3
Revises: ea3a1b2c3d45, ab12cd34ef56
Create Date: 2025-06-15 02:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'f641fa4204d3'
down_revision = ('ea3a1b2c3d45', 'ab12cd34ef56')
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('quorum', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('stage1_locked', sa.Boolean(), nullable=True, server_default=sa.false()))
        batch_op.add_column(sa.Column('stage2_locked', sa.Boolean(), nullable=True, server_default=sa.false()))


def downgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.drop_column('stage2_locked')
        batch_op.drop_column('stage1_locked')
        batch_op.drop_column('quorum')
