"""add comment editing fields"

Revision ID: o1p2q3r4
Revises: l2m3n4o5p6q7
Create Date: 2025-07-02 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'o1p2q3r4'
down_revision = 'l2m3n4o5p6q7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('comments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('edited_at', sa.DateTime(), nullable=True))
    op.create_table(
        'comment_revisions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('comment_id', sa.Integer(), sa.ForeignKey('comments.id')),
        sa.Column('text_md', sa.Text(), nullable=True),
        sa.Column('edited_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('comment_revisions')
    with op.batch_alter_table('comments', schema=None) as batch_op:
        batch_op.drop_column('edited_at')
