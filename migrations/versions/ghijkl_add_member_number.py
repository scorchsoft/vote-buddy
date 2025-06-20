"""add member number to members

Revision ID: ghijkl
Revises: fed1234
Create Date: 2025-06-22 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'ghijkl'
down_revision = 'fed1234'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('members', schema=None) as batch_op:
        batch_op.add_column(sa.Column('member_number', sa.String(length=50), nullable=True))


def downgrade():
    with op.batch_alter_table('members', schema=None) as batch_op:
        batch_op.drop_column('member_number')
