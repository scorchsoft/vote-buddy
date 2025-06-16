"""add notice_date to meetings

Revision ID: d2f3e4f5a6b7
Revises: be52ce2e76d9
Create Date: 2025-06-16 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'd2f3e4f5a6b7'
down_revision = 'be52ce2e76d9'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('notice_date', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.drop_column('notice_date')
