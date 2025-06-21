"""add submission windows and publish flags"""

revision = 's1t2u3v4'
down_revision = 'r1s2t3u4'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('meetings') as batch_op:
        batch_op.add_column(sa.Column('motions_opens_at', sa.DateTime()))
        batch_op.add_column(sa.Column('motions_closes_at', sa.DateTime()))
        batch_op.add_column(sa.Column('amendments_opens_at', sa.DateTime()))
        batch_op.add_column(sa.Column('amendments_closes_at', sa.DateTime()))
        batch_op.add_column(sa.Column('submission_invites_sent_at', sa.DateTime()))
    with op.batch_alter_table('motions') as batch_op:
        batch_op.add_column(sa.Column('is_published', sa.Boolean(), nullable=False, server_default='0'))
    with op.batch_alter_table('amendments') as batch_op:
        batch_op.add_column(sa.Column('is_published', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('amendments') as batch_op:
        batch_op.drop_column('is_published')
    with op.batch_alter_table('motions') as batch_op:
        batch_op.drop_column('is_published')
    with op.batch_alter_table('meetings') as batch_op:
        batch_op.drop_column('submission_invites_sent_at')
        batch_op.drop_column('amendments_closes_at')
        batch_op.drop_column('amendments_opens_at')
        batch_op.drop_column('motions_closes_at')
        batch_op.drop_column('motions_opens_at')
