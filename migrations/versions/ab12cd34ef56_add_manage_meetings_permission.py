"""add manage meetings permission

Revision ID: ab12cd34ef56
Revises: 9769bae50c41
Create Date: 2025-06-14 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'ab12cd34ef56'
down_revision = '9769bae50c41'
branch_labels = None
depends_on = None


def upgrade():
    permissions = sa.table('permissions', sa.column('id', sa.Integer), sa.column('name', sa.String))
    role_permissions = sa.table('roles_permissions', sa.column('role_id', sa.Integer), sa.column('permission_id', sa.Integer))

    op.bulk_insert(permissions, [{'id': 3, 'name': 'manage_meetings'}])
    op.bulk_insert(role_permissions, [
        {'role_id': 1, 'permission_id': 3},
        {'role_id': 2, 'permission_id': 3},
    ])


def downgrade():
    op.execute('DELETE FROM roles_permissions WHERE permission_id=3')
    op.execute('DELETE FROM permissions WHERE id=3')

