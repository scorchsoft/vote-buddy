"""add seconder detail fields

Revision ID: 75c6e4c69f96
Revises: c16b6e000543
Create Date: 2025-06-27 12:21:46.043396

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '75c6e4c69f96'
down_revision = 'c16b6e000543'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('motion_submissions') as batch_op:
        batch_op.add_column(sa.Column('seconder_member_number', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('seconder_name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('allow_clerical', sa.Boolean(), nullable=True, server_default=sa.true()))
        batch_op.add_column(sa.Column('allow_move', sa.Boolean(), nullable=True, server_default=sa.true()))


def downgrade():
    with op.batch_alter_table('motion_submissions') as batch_op:
        batch_op.drop_column('allow_move')
        batch_op.drop_column('allow_clerical')
        batch_op.drop_column('seconder_name')
        batch_op.drop_column('seconder_member_number')
