"""add meeting notice and email settings"""

revision = 't1u2v3w4'
down_revision = 's1t2u3v4'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('meetings') as batch_op:
        batch_op.add_column(sa.Column('notice_md', sa.Text()))
    op.create_table(
        'email_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id'), index=True),
        sa.Column('email_type', sa.String(length=50)),
        sa.Column('auto_send', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )


def downgrade():
    op.drop_table('email_settings')
    with op.batch_alter_table('meetings') as batch_op:
        batch_op.drop_column('notice_md')
