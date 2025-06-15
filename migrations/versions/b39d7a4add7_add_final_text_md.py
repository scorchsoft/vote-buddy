"""add final text field to motions

Revision ID: b39d7a4add7
Revises: 84f4e231e1ac
Create Date: 2025-06-17 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'b39d7a4add7'
down_revision = '84f4e231e1ac'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('motions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('final_text_md', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('motions', schema=None) as batch_op:
        batch_op.drop_column('final_text_md')
