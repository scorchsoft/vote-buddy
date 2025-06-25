"""add indexes for admin log filtering"""

revision = 'v20240704'
down_revision = 'u2v3w4x5'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_index("ix_admin_logs_action", "admin_logs", ["action"])
    op.create_index("ix_admin_logs_created_at", "admin_logs", ["created_at"])


def downgrade():
    op.drop_index("ix_admin_logs_created_at", table_name="admin_logs")
    op.drop_index("ix_admin_logs_action", table_name="admin_logs")
