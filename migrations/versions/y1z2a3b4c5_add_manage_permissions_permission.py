"""add manage permissions permission

Revision ID: y1z2a3b4c5
Revises: v1w2x3y4
Create Date: 2025-08-23 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'y1z2a3b4c5'
down_revision = 'v1w2x3y4'
branch_labels = None
depends_on = None


def upgrade():
    permissions = sa.table('permissions',
        sa.column('id', sa.Integer),
        sa.column('name', sa.String)
    )
    role_permissions = sa.table('roles_permissions',
        sa.column('role_id', sa.Integer),
        sa.column('permission_id', sa.Integer)
    )

    op.bulk_insert(permissions, [{'id': 5, 'name': 'manage_permissions'}])
    op.bulk_insert(role_permissions, [{'role_id': 1, 'permission_id': 5}])


def downgrade():
    op.execute('DELETE FROM roles_permissions WHERE permission_id=5')
    op.execute('DELETE FROM permissions WHERE id=5')
