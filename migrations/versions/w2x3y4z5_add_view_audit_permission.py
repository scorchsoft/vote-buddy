"""add view audit log permission

Revision ID: w2x3y4z5
Revises: v1w2x3y4
Create Date: 2025-07-05 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'w2x3y4z5'
down_revision = 'v1w2x3y4'
branch_labels = None
depends_on = None


def upgrade():
    permissions = sa.table('permissions', sa.column('id', sa.Integer), sa.column('name', sa.String))
    role_permissions = sa.table('roles_permissions', sa.column('role_id', sa.Integer), sa.column('permission_id', sa.Integer))
    op.bulk_insert(permissions, [{'id': 5, 'name': 'view_audit_log'}])
    op.bulk_insert(role_permissions, [{'role_id': 1, 'permission_id': 5}])


def downgrade():
    op.execute('DELETE FROM roles_permissions WHERE permission_id=5')
    op.execute('DELETE FROM permissions WHERE id=5')
