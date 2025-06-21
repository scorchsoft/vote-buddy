"""add submission tokens and seconder fields

Revision ID: r1s2t3u4
Revises: q1w2e3r4
Create Date: 2025-07-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'r1s2t3u4'
down_revision = 'q1w2e3r4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'submission_tokens',
        sa.Column('token', sa.String(length=64), primary_key=True),
        sa.Column('member_id', sa.Integer(), sa.ForeignKey('members.id')),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id')),
        sa.Column('used_at', sa.DateTime(), nullable=True),
    )
    with op.batch_alter_table('motion_submissions') as batch_op:
        batch_op.add_column(sa.Column('member_id', sa.Integer(), sa.ForeignKey('members.id')))
        batch_op.add_column(sa.Column('seconder_id', sa.Integer(), sa.ForeignKey('members.id')))
    with op.batch_alter_table('amendment_submissions') as batch_op:
        batch_op.add_column(sa.Column('member_id', sa.Integer(), sa.ForeignKey('members.id')))
        batch_op.add_column(sa.Column('seconder_id', sa.Integer(), sa.ForeignKey('members.id')))


def downgrade():
    with op.batch_alter_table('amendment_submissions') as batch_op:
        batch_op.drop_column('seconder_id')
        batch_op.drop_column('member_id')
    with op.batch_alter_table('motion_submissions') as batch_op:
        batch_op.drop_column('seconder_id')
        batch_op.drop_column('member_id')
    op.drop_table('submission_tokens')
