"""add board_seconded to amendments

Revision ID: bb1234567890
Revises: 1a2b3c4d5e6f
Create Date: 2025-06-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "bb1234567890"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("amendments", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "board_seconded", sa.Boolean(), nullable=True, server_default=sa.false()
            )
        )


def downgrade():
    with op.batch_alter_table("amendments", schema=None) as batch_op:
        batch_op.drop_column("board_seconded")
