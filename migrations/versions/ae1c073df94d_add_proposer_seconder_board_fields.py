"""add proposer seconder board fields

Revision ID: ae1c073df94d
Revises: 0ed486521334
Create Date: 2025-06-23 21:23:02.590219

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ae1c073df94d'
down_revision = '0ed486521334'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('motions') as batch_op:
        batch_op.add_column(sa.Column('proposer_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('seconder_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('board_proposed', sa.Boolean(), nullable=True, server_default=sa.text('false')))
        batch_op.add_column(sa.Column('board_seconded', sa.Boolean(), nullable=True, server_default=sa.text('false')))
    with op.batch_alter_table('amendments') as batch_op:
        batch_op.add_column(sa.Column('board_proposed', sa.Boolean(), nullable=True, server_default=sa.text('false')))


def downgrade():
    with op.batch_alter_table('amendments') as batch_op:
        batch_op.drop_column('board_proposed')
    with op.batch_alter_table('motions') as batch_op:
        batch_op.drop_column('board_seconded')
        batch_op.drop_column('board_proposed')
        batch_op.drop_column('seconder_id')
        batch_op.drop_column('proposer_id')
