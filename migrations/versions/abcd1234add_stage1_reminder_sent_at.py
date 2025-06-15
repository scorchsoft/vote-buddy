"""add stage1_reminder_sent_at column

Revision ID: abcd1234
Revises: f641fa4204d3
Create Date: 2025-06-17 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'abcd1234'
down_revision = 'f641fa4204d3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('stage1_reminder_sent_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.drop_column('stage1_reminder_sent_at')
