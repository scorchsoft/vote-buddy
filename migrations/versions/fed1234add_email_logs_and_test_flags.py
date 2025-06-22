"""add email logs and test flags

Revision ID: fed1234
Revises: fcdb1234
Create Date: 2025-06-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'fed1234'
down_revision = 'fcdb1234'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('members', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_test', sa.Boolean(), nullable=True, server_default=sa.text('false')))
    with op.batch_alter_table('vote_tokens', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_test', sa.Boolean(), nullable=True, server_default=sa.text('false')))
    with op.batch_alter_table('votes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_test', sa.Boolean(), nullable=True, server_default=sa.text('false')))
    op.create_table(
        'email_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id')),
        sa.Column('member_id', sa.Integer(), sa.ForeignKey('members.id')),
        sa.Column('type', sa.String(length=50)),
        sa.Column('is_test', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('sent_at', sa.DateTime(), nullable=True)
    )


def downgrade():
    op.drop_table('email_logs')
    with op.batch_alter_table('votes', schema=None) as batch_op:
        batch_op.drop_column('is_test')
    with op.batch_alter_table('vote_tokens', schema=None) as batch_op:
        batch_op.drop_column('is_test')
    with op.batch_alter_table('members', schema=None) as batch_op:
        batch_op.drop_column('is_test')
