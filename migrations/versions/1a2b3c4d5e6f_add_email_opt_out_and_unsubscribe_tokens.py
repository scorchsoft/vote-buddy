"""add email opt out and unsubscribe tokens

Revision ID: 1a2b3c4d5e6f
Revises: fa1e1fb8c1a0
Create Date: 2025-06-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '1a2b3c4d5e6f'
down_revision = 'fa1e1fb8c1a0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('members', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email_opt_out', sa.Boolean(), nullable=True, server_default=sa.false()))
    op.create_table(
        'unsubscribe_tokens',
        sa.Column('token', sa.String(length=36), primary_key=True),
        sa.Column('member_id', sa.Integer(), sa.ForeignKey('members.id')),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('unsubscribe_tokens')
    with op.batch_alter_table('members', schema=None) as batch_op:
        batch_op.drop_column('email_opt_out')
