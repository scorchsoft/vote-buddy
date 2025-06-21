"""add stage2_reminder_sent_at column

Revision ID: q1w2e3r4
Revises: p1q2r3s4
Create Date: 2025-07-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'q1w2e3r4'
down_revision = 'p1q2r3s4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('stage2_reminder_sent_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.drop_column('stage2_reminder_sent_at')
