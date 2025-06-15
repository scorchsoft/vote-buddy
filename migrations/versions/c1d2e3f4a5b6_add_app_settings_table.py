"""add app settings table and manage_settings permission

Revision ID: c1d2e3f4a5b6
Revises: fa1e1fb8c1a0
Create Date: 2025-06-17 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'c1d2e3f4a5b6'
down_revision = 'fa1e1fb8c1a0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'app_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('key', sa.String(length=50), nullable=False, unique=True),
        sa.Column('value', sa.String(length=255), nullable=True),
        sa.Column('group', sa.String(length=50), nullable=True),
    )

    permissions = sa.table('permissions', sa.column('id', sa.Integer), sa.column('name', sa.String))
    role_permissions = sa.table('roles_permissions', sa.column('role_id', sa.Integer), sa.column('permission_id', sa.Integer))

    op.bulk_insert(permissions, [{'id': 4, 'name': 'manage_settings'}])
    op.bulk_insert(role_permissions, [{'role_id': 1, 'permission_id': 4}])


def downgrade():
    op.execute('DELETE FROM roles_permissions WHERE permission_id=4')
    op.execute('DELETE FROM permissions WHERE id=4')
    op.drop_table('app_settings')
