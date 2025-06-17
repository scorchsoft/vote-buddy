"""add comments support"""

from alembic import op
import sqlalchemy as sa

revision = 'fcdb1234'
down_revision = 'b39d7a4add7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('meetings', sa.Column('comments_enabled', sa.Boolean(), nullable=True, server_default=sa.false()))
    op.add_column('members', sa.Column('can_comment', sa.Boolean(), nullable=True, server_default=sa.true()))
    op.create_table(
        'comments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id')),
        sa.Column('motion_id', sa.Integer(), sa.ForeignKey('motions.id'), nullable=True),
        sa.Column('amendment_id', sa.Integer(), sa.ForeignKey('amendments.id'), nullable=True),
        sa.Column('member_id', sa.Integer(), sa.ForeignKey('members.id')),
        sa.Column('text_md', sa.Text(), nullable=True),
        sa.Column('hidden', sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('comments')
    with op.batch_alter_table('members', schema=None) as batch_op:
        batch_op.drop_column('can_comment')
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.drop_column('comments_enabled')
