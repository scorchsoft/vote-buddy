"""add amendment objections table"""

revision = 'e3b1c6d7e4'
down_revision = 'fa1e1fb8c1a0'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


def upgrade():
    op.create_table(
        'amendment_objections',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('amendment_id', sa.Integer(), sa.ForeignKey('amendments.id')),
        sa.Column('member_id', sa.Integer(), sa.ForeignKey('members.id')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('amendment_objections')
