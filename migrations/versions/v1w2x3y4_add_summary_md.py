"""add meeting summary field

Revision ID: v1w2x3y4
Revises: u2v3w4x5
Create Date: 2025-07-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'v1w2x3y4'
down_revision = 'u2v3w4x5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('summary_md', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.drop_column('summary_md')
