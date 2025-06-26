"""ensure root admin role has manage_users permission

Revision ID: x4y5z6
Revises: w2x3y4z5
Create Date: 2025-08-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'x4y5z6'
down_revision = 'w2x3y4z5'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    role_id = conn.execute(sa.text("SELECT id FROM roles WHERE name='root_admin'")).scalar()
    perm_id = conn.execute(sa.text("SELECT id FROM permissions WHERE name='manage_users'")).scalar()
    if role_id and perm_id:
        exists = conn.execute(sa.text(
            "SELECT 1 FROM roles_permissions WHERE role_id=:r AND permission_id=:p"),
            {"r": role_id, "p": perm_id}
        ).first()
        if not exists:
            conn.execute(sa.text(
                "INSERT INTO roles_permissions (role_id, permission_id) VALUES (:r, :p)"),
                {"r": role_id, "p": perm_id}
            )


def downgrade():
    conn = op.get_bind()
    role_id = conn.execute(sa.text("SELECT id FROM roles WHERE name='root_admin'")).scalar()
    perm_id = conn.execute(sa.text("SELECT id FROM permissions WHERE name='manage_users'")).scalar()
    if role_id and perm_id:
        conn.execute(sa.text(
            "DELETE FROM roles_permissions WHERE role_id=:r AND permission_id=:p"),
            {"r": role_id, "p": perm_id}
        )
