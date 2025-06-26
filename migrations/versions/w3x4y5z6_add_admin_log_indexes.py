"""add indexes on admin_logs action and created_at

Revision ID: w3x4y5z6
Revises: r3s4t5u6
Create Date: 2025-07-20 00:00:00.000001
"""
from alembic import op
import sqlalchemy as sa

revision = 'w3x4y5z6'
down_revision = 'r3s4t5u6'
branch_labels = None
depends_on = None


def upgrade():
    # Check if indexes already exist before creating them
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('admin_logs')]
    
    if 'ix_admin_logs_action' not in existing_indexes:
        op.create_index('ix_admin_logs_action', 'admin_logs', ['action'])
    
    if 'ix_admin_logs_created_at' not in existing_indexes:
        op.create_index('ix_admin_logs_created_at', 'admin_logs', ['created_at'])


def downgrade():
    op.drop_index('ix_admin_logs_created_at', table_name='admin_logs')
    op.drop_index('ix_admin_logs_action', table_name='admin_logs')
