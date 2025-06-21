"""add admin logs table

Revision ID: o3p4q5r6
Revises: n1o2p3q4
Create Date: 2025-06-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'o3p4q5r6'
down_revision = 'n1o2p3q4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'admin_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('action', sa.String(length=50), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('admin_logs')
