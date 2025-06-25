"""add indexes on admin_logs action and created_at

Revision ID: w2x3y4z5
Revises: r3s4t5u6
Create Date: 2025-07-20 00:00:00.000001
"""
from alembic import op
import sqlalchemy as sa

revision = 'w2x3y4z5'
down_revision = 'r3s4t5u6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_admin_logs_action', 'admin_logs', ['action'])
    op.create_index('ix_admin_logs_created_at', 'admin_logs', ['created_at'])


def downgrade():
    op.drop_index('ix_admin_logs_created_at', table_name='admin_logs')
    op.drop_index('ix_admin_logs_action', table_name='admin_logs')
