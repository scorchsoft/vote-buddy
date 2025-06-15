"""add public results flag

Revision ID: 84f4e231e1ac
Revises: f641fa4204d3, f3a0d98b5c17, 12345add
Create Date: 2025-06-16 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '84f4e231e1ac'
down_revision = ('f641fa4204d3', 'f3a0d98b5c17', '12345add')
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('public_results', sa.Boolean(), nullable=True, server_default=sa.false()))


def downgrade():
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.drop_column('public_results')
