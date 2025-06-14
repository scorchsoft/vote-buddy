"""add motion_md to meetings

Revision ID: ccd9d99d0db0
Revises: 4b7aeabb87a7
Create Date: 2025-06-15 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'ccd9d99d0db0'
down_revision = '4b7aeabb87a7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('motion_md', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.drop_column('motion_md')
