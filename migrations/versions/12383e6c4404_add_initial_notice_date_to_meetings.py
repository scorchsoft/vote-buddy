"""add_initial_notice_date_to_meetings

Revision ID: 12383e6c4404
Revises: 868e8e5a5b92
Create Date: 2025-06-27 21:43:36.229842

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '12383e6c4404'
down_revision = '868e8e5a5b92'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('initial_notice_date', sa.DateTime(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.drop_column('initial_notice_date')

    # ### end Alembic commands ###
