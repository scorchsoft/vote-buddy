"""add tie_break_method to amendments

Revision ID: fa1e1fb8c1a0
Revises: abcd1234
Create Date: 2025-06-19 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'fa1e1fb8c1a0'
down_revision = 'abcd1234'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('amendments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tie_break_method', sa.String(length=20), nullable=True))


def downgrade():
    with op.batch_alter_table('amendments', schema=None) as batch_op:
        batch_op.drop_column('tie_break_method')
